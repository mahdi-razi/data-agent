import contextlib
import glob
import io
import json
import os
import sys
from functools import partial
import traceback

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from charts import save_chart, save_dashboard

WORK = "/work" 

namespace = {
    "pd": pd,
    "np": np,
    "stats": stats,
    "sm": sm,
    "smf": smf,
    "px": px,
    "go": go,
    "save_chart": partial(save_chart, folder=WORK),
    "save_dashboard": partial(save_dashboard, folder=WORK),
}

os.chdir(WORK)

loaded = {}


def load_new_files():
    for path in glob.glob(os.path.join(WORK, "*.parquet")):
        modified = os.path.getmtime(path)
        if loaded.get(path) != modified:
            name = os.path.splitext(os.path.basename(path))[0]
            namespace[name] = pd.read_parquet(path)
            loaded[path] = modified


def run(code):
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(code, namespace)
    except Exception:
        return f"{output.getvalue()}{traceback.format_exc()}"
    text = output.getvalue() or "(no output)"
    return text


def main():
    for line in sys.stdin:
        code = json.loads(line)["code"]
        load_new_files()
        print(json.dumps({"output": run(code)}), flush=True)


if __name__ == "__main__":
    main()