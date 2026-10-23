# Charts
Use Plotly Express (px).Save with save_chart(fig, "short_name") and tell the user the file name.
Files are .html.
Never call fig.show(). You cannot see the chart, so describe findings with numbers you computed.

## Pick the chart
| Showing                          | Use                                        |
| trend over time                  | line (group by day/month, sort by date)    |
| compare categories               | bar                                        |
| ranking                          | horizontal bar, sorted by value            |
| part of a whole (under 6 parts)  | stacked bar (not pie)                      |
| distribution of one number       | histogram                                  |
| compare distributions by group   | box plot                                   |
| two numbers                      | scatter (size= for a third number)         |
| many numbers                     | correlation heatmap                        |
| same chart for several groups    | facet_col= (small multiples)               |

Never: 3D charts, pie charts with 6+ slices, dual-axis charts.

## Patterns
    px.line(df, x='date', y='value', color='category', markers=True, title='...', labels={'value': 'Revenue ($)', 'date': 'Month'})
    px.bar(df.sort_values('metric'), x='metric', y='category', orientation='h', text_auto=',.0f', title='...', labels={'metric': '...', 'category': '...'})
    px.bar(df, x='category', y='share', color='category', color_discrete_sequence=px.colors.qualitative.Safe, title='...', labels={'share': 'Share (%)'})
    px.histogram(df, x='value', nbins=30, marginal='box', title='...', labels={'value': '...'})
    px.box(df, x='group', y='value', title='...', labels={'value': '...'})
    px.scatter(df, x='x', y='y', title='...', labels={'x': '...', 'y': '...'})
    px.imshow(df.corr(numeric_only=True), text_auto='.2f', color_continuous_scale='RdBu_r', zmin=-1, zmax=1, title='...')
    px.line(df, x='date', y='value', facet_col='category', facet_col_wrap=3, title='...')
    print(save_chart(fig, "revenue_by_month"))

## Rules
- Always set a title and axis labels with title= and labels={...}. Include units.
- Compute the number first, then use it in the title ("Revenue grew 23% year over year"). If you have no number, use a plain title.
- Sort bars by value, unless the order is natural (months, stages).
- More than 8 categories: show the top 8 and group the rest as "Other", or use a horizontal bar.
- Use px.colors.qualitative.Safe (colorblind-safe). Never rely on red vs green alone.
- Thousands of rows: aggregate first, or sample at most 5000 rows.
- Several charts side by side: use the same axis range when comparing.