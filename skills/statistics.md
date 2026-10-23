# Statistics
Before any test: drop missing values and say how many rows were used.
Report the effect size with its 95% confidence interval, then the p-value. Never a p-value alone.

## Describe first
- For every numeric column report the mean AND the median. A big gap means the data is skewed: lead with the median.
- Spread: standard deviation for symmetric data, IQR for skewed data.
- For skewed metrics (revenue, durations) also report p50, p90, p99: df['x'].quantile([0.5, 0.9, 0.99])

## Pick the test
| Question                                   | Test                               |
| two group means                            | Welch t-test                       |
| two groups, skewed or ordinal data         | Mann-Whitney U                     |
| same entities before vs after              | paired t-test                      |
| three or more group means                  | ANOVA                              |
| two rates (conversion, churn)              | z-test for proportions             |
| two categorical columns                    | chi-squared                        |
| two numbers                                | Pearson (Spearman if skewed)       |
| what drives an outcome, several factors    | regression                         |

## Recipes
Two groups, Welch t-test:
    a = df[df['group'] == 'A']['value'].dropna()
    b = df[df['group'] == 'B']['value'].dropna()
    result = stats.ttest_ind(a, b, equal_var=False)
    ci = result.confidence_interval()
    print(a.mean() - b.mean(), ci.low, ci.high, result.pvalue)

Two groups, skewed data (also print both medians):
    result = stats.mannwhitneyu(a, b)
    print(a.median(), b.median(), result.pvalue)

Before/after on the same rows:
    result = stats.ttest_rel(df['after'], df['before'])
    ci = result.confidence_interval()
    print((df['after'] - df['before']).mean(), ci.low, ci.high, result.pvalue)

Three or more groups:
    groups = [g['value'].dropna() for _, g in df.groupby('group')]
    print(stats.f_oneway(*groups))

Two rates (x = events, n = rows in each group):
    p1, p2 = x1 / n1, x2 / n2
    se = (p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2) ** 0.5
    stat, p = sm.stats.proportions_ztest([x1, x2], [n1, n2])
    print(p1 - p2, p1 - p2 - 1.96 * se, p1 - p2 + 1.96 * se, p)

Two categorical columns:
    table = pd.crosstab(df['a'], df['b'])
    chi2, p, dof, _ = stats.chi2_contingency(table)
    v = (chi2 / (table.values.sum() * (min(table.shape) - 1))) ** 0.5   # Cramer's V, the effect size
    print(table, p, v)

Confidence interval of a mean:
    values = df['price'].dropna()
    low, high = stats.t.interval(0.95, len(values) - 1, loc=values.mean(), scale=stats.sem(values))

Correlation (spearmanr if skewed):
    clean = df[['x', 'y']].dropna()
    r, p = stats.pearsonr(clean['x'], clean['y'])

Regression for a number:
    model = smf.ols('price ~ x + C(region)', data=df).fit()
    print(model.summary().tables[1]); print(model.rsquared, int(model.nobs))

Regression for yes/no outcomes such as churn (make a 0/1 column first):
    model = smf.logit('churned_flag ~ tenure + C(plan)', data=df).fit(disp=False)
    print(model.summary().tables[1]); print(np.exp(model.params))   # odds ratios

## Trends over time
- Group by day, week or month and sort by date first. Smooth with df['x'].rolling(7).mean().
- Compare the same period (this March vs last March) so seasonality is not mistaken for a trend.
- Do not forecast. Describe what happened.

## Be careful with claims
- Say "associated with", never "causes". Consider reverse causation and confounders.
- Statistically significant is not the same as big. Always say how large the difference is and whether it matters.
- p-values below 0.001 are written "<0.001", never "0.0000".
- Fewer than about 30 rows in a group, or heavily skewed data: say the result is less reliable.
- Many tests: say how many you ran. With 20 tests at 0.05, about one is "significant" by chance. Bonferroni: divide 0.05 by the number of tests.
- Say who is missing from the data when it matters (dropped rows, churned customers).