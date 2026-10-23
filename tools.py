from langchain_core.tools import tool
import os
import psycopg
import pandas as pd
import json
from langchain_core.runnables import RunnableConfig
import subprocess
import threading
import uuid
from decimal import Decimal
from datetime import date


CAP = 100_000
TIMEOUT = 60
RESERVED = {"pd", "np", "stats", "sm", "smf", "px", "go", "save_chart", "save_dashboard"}
MAX_OUTPUT = 5000

sandboxes = {}


def project_folder(config):
    return os.path.join("outputs", config["configurable"]["thread_id"])


def connect():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        options="-c default_transaction_read_only=on"
    )


def get_sandbox(config):
    project = config["configurable"]["thread_id"]
    process, name = sandboxes.get(project, (None, None))

    if process is None or process.poll() is not None:
        folder = os.path.abspath(project_folder(config))
        os.makedirs(folder, exist_ok=True)
        name = f"ds-{project}-{uuid.uuid4().hex[:6]}"
        process = subprocess.Popen(
            ["docker", "run", "-i", "--rm", "--name", name,
             "--network", "none", "--memory", "1g", "--cpus", "1",
             "-v", f"{folder}:/work", "ds-sandbox"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        sandboxes[project] = (process, name)

    return process, name


def kill_container(name):
    subprocess.run(["docker", "kill", name], capture_output=True)


@tool
def run_python(code: str, config: RunnableConfig) -> str:
    """
    Run Python in a sandbox. Only print() output comes back (max 5000 chars), so print results.
    Variables persist between calls. DataFrames from load_query are already loaded by name.
    Already imported: pd, np, stats, sm, smf, px, go. No internet, 60s limit.
    Charts (only if asked): save_chart(fig, name) or save_dashboard(figures, title, name, kpis).
    """
    
    process, name = get_sandbox(config)

    process.stdin.write(json.dumps({"code": code}) + "\n")
    process.stdin.flush()

    timer = threading.Timer(TIMEOUT, kill_container, args=[name])
    timer.start()
    line = process.stdout.readline()
    timer.cancel()

    if not line:
        sandboxes.pop(config["configurable"]["thread_id"], None)
        return (
            "Error: the sandbox stopped. Variables you created are lost. DataFrames from load_query come back automatically."
        )

    output = json.loads(line)["output"]

    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + f"\n (truncated. Print less.)"
    return output


@tool
def get_schema() -> str:
    """List the tables and columns of the database."""
    sql = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
    """
    try:
        with connect() as conn:
            rows = conn.execute(sql).fetchall()
    except Exception as e:
        return f"Error: {e}"

    tables = {}

    for table, column, data_type in rows:
        if table not in tables:
            tables[table] = []

        tables[table].append(f"{column} ({data_type})")

    result = []

    for table, columns in tables.items():
        column_list = ", ".join(columns)
        result.append(f"{table}: {column_list}")

    return "\n".join(result)


@tool
def load_query(sql: str, name: str, config: RunnableConfig) -> str:
    """
    Run a read-only SQL SELECT and store the result as a pandas DataFrame called `name`. Returns the shape and the first 5 rows.
    """
    if not name.isidentifier():
        return "Error: name must be a valid Python variable name"
    if name in RESERVED:
        return f"Error: {name} is reserved, pick another name"

    sql = sql.strip().rstrip(";")
    query = f"SELECT * FROM (\n{sql}\n) AS q LIMIT {CAP}"

    try:
        with connect() as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()

            column_names = []
            for column in cursor.description:
                column_names.append(column.name)
    except Exception as error:
        return f"Error: {error}"

    df = pd.DataFrame(rows, columns=column_names)

    for col in df.columns:
       if df[col].map(lambda v: isinstance(v, Decimal)).any():
           df[col] = df[col].astype(float)
       elif df[col].map(lambda v: isinstance(v, date)).any():
           df[col] = pd.to_datetime(df[col])

    folder = project_folder(config)
    os.makedirs(folder, exist_ok=True)
    try:
        df.to_parquet(os.path.join(folder, name + ".parquet"))
    except Exception as e:
        return f"Error: could not save {name}: {e}"

    message = f"Loaded {name}: {len(df)} rows x {len(df.columns)} columns"
    if len(df) == CAP:
        message += f" (capped at {CAP} rows)"

    message += "\n" + df.head().to_string()

    return message


@tool
def profiler(name: str, config: RunnableConfig) -> str:
    """
    Describe every column of a DataFrame loaded with load_query, as JSON: missing values,
    unique count, for number columns the min, median, mean, max and outlier count, and for all
    other columns the most common values and any hidden missing value candidates (like N/A or blank text).
    """
    path = os.path.join(project_folder(config), name + ".parquet")

    if not name.isidentifier() or not os.path.exists(path):
        return f"Error: there is no DataFrame called {name}. Load it with load_query first."

    df = pd.read_parquet(path)
    row_count = len(df)

    if row_count == 0:
        return f"{name} is empty (0 rows)."

    column_reports = []

    for column in df.columns:
        series = df[column]

        missing_count = int(series.isna().sum())
        unique_count = int(series.astype(str).nunique())

        column_report = {
            "name": str(column),
            "type": str(series.dtype),
            "missing_count": missing_count,
            "missing_percent": round(100 * missing_count / row_count, 1),
            "unique_count": unique_count,
        }

        is_number = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)

        if is_number:
            values = series.dropna()

            if len(values) > 0:
                q1 = values.quantile(0.25)
                q3 = values.quantile(0.75)
                d = q3 - q1
                low_limit = q1 - 1.5 * d
                high_limit = q3 + 1.5 * d

                outliers = values[(values < low_limit) | (values > high_limit)]

                column_report["min"] = float(values.min())
                column_report["median"] = float(values.median())
                column_report["mean"] = round(float(values.mean()), 4)
                column_report["max"] = float(values.max())
                column_report["outlier_count"] = int(len(outliers))
        else:
            value_counts = series.dropna().astype(str).value_counts().head()

            top_values = {}
            for value, count in value_counts.items():
                top_values[value[:50]] = int(count)

            column_report["top_values"] = top_values

            text_values = series.dropna().astype(str)
            cleaned_values = text_values.str.strip().str.lower()

            hidden_missing = {}

            blank_count = int((cleaned_values == "").sum())
            if blank_count > 0:
                hidden_missing["(blank)"] = blank_count

            for p in ["n/a", "na", "null", "none", "-", "?", "unknown"]:
                p_count = int((cleaned_values == p).sum())
                if p_count > 0:
                    hidden_missing[p] = p_count

            if len(hidden_missing) > 0:
                column_report["hidden_missing_candidates"] = hidden_missing

        column_reports.append(column_report)

    report = {
        "dataframe": name,
        "row_count": row_count,
        "column_count": len(df.columns),
        "duplicate_rows": int(df.astype(str).duplicated().sum()),
        "columns": column_reports,
    }

    return json.dumps(report, ensure_ascii=False)