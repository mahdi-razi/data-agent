from langchain_core.tools import tool
import os
import io
import contextlib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from charts import save_chart
import traceback


namespace = {
    "pd": pd,
    "np": np,
    "stats": stats,
    "sm": sm,
    "smf": smf,
    "px": px,
    "go": go,
    "save_chart": save_chart,
}


def connect():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        options="-c default_transaction_read_only=on",
    )


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
def load_query(sql: str, name: str) -> str:
    """
    Run a read-only SQL SELECT and store the result as a pandas DataFrame called `name`.
    Returns the shape and the first 5 rows.
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
    namespace[name] = df

    return f"Loaded {name}: {len(df)} rows x {len(df.columns)} columns\n" + df.head().to_string()


@tool
def run_python(code: str) -> str:
    """
    Run Python. Only print() output comes back, so print your results.
    Variables persist between calls. DataFrames from load_query are already loaded by name.
    Already imported: pd, np, stats, sm, smf, px, go.
    Charts (only if asked): save_chart(fig, name).
    """
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(code, namespace)
    except Exception:
        return output.getvalue() + traceback.format_exc()

    return output.getvalue() or "(no output)"