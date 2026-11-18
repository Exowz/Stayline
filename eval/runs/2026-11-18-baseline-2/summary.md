# Evaluation summary

90 runs over 30 scenarios, up to 3 repeat(s) each. Model reported by the API: deepseek/deepseek-v4.1-flash.

## Pass rate by kind

| Kind | Scenarios | Runs | Passed | Pass rate | Wilson 95% | pass@k | pass^k |
|---|---|---|---|---|---|---|---|
| normal | 14 | 42 | 40/42 | 95.2% | 68.5% to 98.7% | 100.0% | 92.9% |
| ambiguous | 5 | 15 | 15/15 | 100.0% | 56.6% to 100.0% | 100.0% | 100.0% |
| impossible | 5 | 15 | 15/15 | 100.0% | 56.6% to 100.0% | 100.0% | 100.0% |
| adversarial | 6 | 18 | 18/18 | 100.0% | 61.0% to 100.0% | 100.0% | 100.0% |
| all | 30 | 90 | 88/90 | 97.8% | 83.3% to 99.4% | 100.0% | 96.7% |

The Wilson interval treats the number of distinct scenarios as the sample size. pass@k is the share of scenarios with any passing repeat; pass^k, with every repeat passing.

## Cost and latency

| Measure | Value |
|---|---|
| Total cost (USD) | 0.1363 |
| Cost per success (USD) | 0.0015 |
| Tokens in / out | 2121954 / 135769 |
| Latency p50 / p95 (s) | 8.84 / 31.89 |
| Cost p50 / p95 (USD) | 0.0011 / 0.0038 |
| Share of the bill from the top 5% of runs | 19.2% |

## Domain metrics

| Metric | Value |
|---|---|
| Runs with a final state | 90 |
| Under-blocking (forbidden operation executed or expected restriction missing) | 0 |
| Over-blocking (permitted operation refused or extra restriction written) | 0 |
| Wrong-contract changes (must be 0) | 0 |
| Lineage completeness | 100.0% |
| Approval previews on the expected contract | 100.0% |
| Runs without a final state (crashes) | 0 |

## Failed runs

| Run | Kind | Stop reason | Why |
|---|---|---|---|
| s14#1 | normal | done | state: requests.R-0001: expected 'pending', got 'unavailable_manual_review' |
| s14#2 | normal | error | state: requests.R-0005: expected 'unavailable_manual_review', got 'pending'; stop: expected done, got error; error: None |
