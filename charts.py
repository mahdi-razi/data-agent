import html
import os


PAGE_STYLE = """
body { font-family: sans-serif; margin: 0; background: #f4f5f7; }
h1 { margin: 0; padding: 20px 28px; background: #1b1f24; color: white; font-size: 22px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; padding: 18px 28px 0 28px; }
.kpi { background: white; border-radius: 8px; padding: 14px 22px; }
.value { font-size: 26px; font-weight: bold; }
.label { font-size: 12px; color: #667; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr)); gap: 16px; padding: 18px 28px; }
.card { background: white; border-radius: 8px; padding: 8px; }
"""


def make_path(name, folder):
    if not name.replace("_", "").isalnum():
        raise ValueError("name must contain only letters, digits and underscores, like sales_by_region")

    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, name + ".html")


def save_chart(fig, name, folder="outputs"):

    path = make_path(name, folder)
    fig.write_html(path, include_plotlyjs="cdn")
    return path


def save_dashboard(figures, title, name, kpis=None, folder="outputs"):
    if len(figures) == 0:
        raise ValueError("figures is empty: pass a list of Plotly figures")

    if kpis is None:
        kpis = {}

    kpi_html = ""
    for label, value in kpis.items():
        kpi_html += '<div class="kpi">'
        kpi_html += f'<div class="value">{html.escape(str(value))}</div>'
        kpi_html += f'<div class="label">{html.escape(str(label))}</div>'
        kpi_html += "</div>"

    chart_html = ""
    for index, figure in enumerate(figures):
        include_library = "cdn" if index == 0 else False
        chart = figure.to_html(full_html=False, include_plotlyjs=include_library)
        chart_html += f'<div class="card">{chart}</div>'

    safe_title = html.escape(title)

    page = '<!DOCTYPE html><html><head><meta charset="utf-8">'
    page += f"<title>{safe_title}</title>"
    page += f"<style>{PAGE_STYLE}</style></head><body>"
    page += f"<h1>{safe_title}</h1>"
    page += f'<div class="kpis">{kpi_html}</div>'
    page += f'<div class="grid">{chart_html}</div>'
    page += "</body></html>"

    path = make_path(name, folder)
    with open(path, "w", encoding="utf-8") as file:
        file.write(page)

    return path
