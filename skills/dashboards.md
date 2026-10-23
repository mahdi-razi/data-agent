# Dashboards
A dashboard is a few KPI numbers on top and several charts below, saved as ONE HTML file with save_dashboard.
Never use save_chart for a dashboard. Never write HTML or JavaScript yourself.

## Before building
Settle these from the request.
- The 3 or 4 numbers that matter most.
- What to break them down by (time, region, product, ...).
Use get_schema to find the right tables. If the database has no suitable data, say so. Never invent data.

## Steps
1. One load_query per group of charts, aggregated in SQL. A monthly trend is 12 to 36 rows, not 50000 raw rows.
2. Compute the KPIs in run_python from the loaded data. When there is a date column, add the change vs the previous period.
3. Build 4 to 6 figures, each answering a DIFFERENT question:
   - trend over time
   - breakdown by a category (bar)
   - ranking (horizontal bar, top 10)
   - distribution (histogram or box)
   - relationship between two numbers (scatter)
   Do not draw the same information twice.
4. Put the most important chart first. Charts appear in list order, left to right, then down.
5. Call save_dashboard, print the returned path, and tell the user the file name.

## Call
    figures = [fig_trend, fig_by_region, fig_top_products, fig_distribution]
    kpis = {
        "Total revenue": "1.2M (+8% vs last month)",
        "Orders": "15.6K",
        "Avg order value": "$127",
        "Period": "Jan 2024 - Jun 2024",
    }
    print(save_dashboard(figures, "Sales overview", "sales_overview", kpis=kpis))

## Rules
- 3 or 4 KPIs, as readable text ("1.2M", "$127", "8.4%"), never "1203948.3".
- Always include the date range as a KPI, so the reader knows what the snapshot covers.
- Plot aggregated data, not raw rows. Keep the whole dashboard well under 10000 rows of data.
- Line charts: under 500 points per series (switch to weekly or monthly if more). Scatter: sample at most 1000 points.
- If a query hit the row cap, say so in your answer.
- After saving, summarize the 2 or 3 main findings using numbers you computed. You cannot see the dashboard.