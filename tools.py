from langchain_core.tools import tool
import os
import psycopg
import pandas as pd
import json
from langchain_core.runnables import RunnableConfig
import subprocess
import threading
import uuid


TIMEOUT = 60

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
    Run Python in a sandbox. Only print() output comes back, so print results.
    Variables persist between calls. DataFrames from load_query are already loaded by name.
    Already imported: pd, np, stats, sm, smf, px, go. No internet, 60s limit.
    Charts (only if asked): save_chart(fig, name).
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
        return "Error: the sandbox stopped. Variables you created are lost. DataFrames from load_query come back automatically."

    return json.loads(line)["output"]


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

    try:
        with connect() as conn:
            cursor = conn.execute(sql.strip().rstrip(";"))
            rows = cursor.fetchall()
            column_names = [column.name for column in cursor.description]
    except Exception as error:
        return f"Error: {error}"

    df = pd.DataFrame(rows, columns=column_names)

    folder = project_folder(config)
    os.makedirs(folder, exist_ok=True)
    df.to_parquet(os.path.join(folder, name + ".parquet"))

    return f"Loaded {name}: {len(df)} rows x {len(df.columns)} columns\n" + df.head().to_string()