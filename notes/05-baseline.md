# The vLLM baseline on one NVIDIA L4

## Why

The lab needs a reference point for judging each optimization. The latency target is a first text or tool-call chunk within one second at p90. The separate quality check measures exact matches on tool names and arguments.

## Expected behavior

The study plan identified KV-cache pressure as a possible limit when more conversations share one L4. The baseline establishes where latency crosses the target. Identifying the bottleneck requires engine telemetry and a profiler trace at that load.

## What we measured

Gemma 4 E4B ran on vLLM `v0.33.0` on one `g6.xlarge` in `eu-west-3`. The server used a 16,384-token context limit, an 80-sequence cap, chunked prefill and a batch budget of 1,024 tokens. The Job warmed the engine with four users for 60 seconds, then exercised seven loads with a 180-second request-start window each. Each turn included tools and allowed up to 300 output tokens. [Deployment](../k8s/vllm.yaml) · [Benchmark Job](../k8s/bench-job.tmpl.yaml)

| Concurrent users | Measured requests | p90 time to first output | Requests with output in under 1 s |
| ---: | ---: | ---: | ---: |
| 1 | 44 | 77.07 ms | 44 / 44 |
| 2 | 100 | 138.11 ms | 100 / 100 |
| 4 | 201 | 151.26 ms | 201 / 201 |
| 8 | 414 | 160.02 ms | 414 / 414 |
| 16 | 789 | 266.50 ms | 789 / 789 |
| 32 | 1,244 | 1,262.50 ms | 1,082 / 1,244 |
| 64 | 1,332 | 8,839.95 ms | 110 / 1,332 |

All 4,124 measured requests produced visible output. The separate evaluation matched **130 of 200** expected tool-call sets (**65%**). [Raw timings](../results/baseline%20%28vLLM%29/) · [Quality score](../results/baseline%20%28vLLM%29/quality.txt)

![vLLM p90 time to first output rises above the one-second target at 32 users](../results/baseline%20%28vLLM%29/p90_ttft.png)

## What we learned

The highest tested load under the latency target was **16 users**. At 32 users the engine still delivered 233.10 streamed chunks/s, up from 142.56 at 16 users, but only 87.0% of requests started receiving output within one second. Optimizing for throughput alone would favor running at a load that already misses the latency objective. [Summary calculation](../analysis/summarize.py)

## Decision

Use 16 users and 65% tool-call exact match as the capacity and quality references for vLLM tuning. Inspect the 32-user case first when diagnosing where requests start waiting. [Engine comparison](08-engine-comparison.md)
