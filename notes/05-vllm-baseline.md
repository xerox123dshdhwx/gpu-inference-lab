# The vLLM baseline on one NVIDIA L4

Gemma 4 E4B ran in BF16 on one `g6.xlarge` in Paris. Chunked prefill with **`--max-num-batched-tokens=1024`** left room for the KV cache by spreading long prompts across scheduling steps. The per-request context limit was 16,384 tokens and the sequence ceiling was 80 for up to 64 concurrent users. [Deployment manifest](../k8s/vllm.yaml)

vLLM `v0.33.0` kept Gemma 4’s default of thinking off and used automatic tool choice with the `gemma4` parser. [Reasoning settings](https://docs.vllm.ai/en/v0.33.0/features/reasoning_outputs/)

**At 16 concurrent users, p90 time to first output was 267 ms.** All 4,124 measured requests produced text or a tool call. In the separate quality evaluation, tool-call exact match was **65% (130/200)**. [Raw timings](../results/baseline%20%28vLLM%29/) · [Quality score](../results/baseline%20%28vLLM%29/quality.txt)

| Users | First output < 1 s / total | p50 TTFT (ms) | p90 TTFT (ms) | Est. chunk gap (ms) | Chunks/s | Errors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 44 / 44 | 67.54 | 77.07 | 40.74 | 11.95 | 0 |
| 2 | 100 / 100 | 70.93 | 138.11 | 41.51 | 19.63 | 0 |
| 4 | 201 / 201 | 127.12 | 151.26 | 42.21 | 41.37 | 0 |
| 8 | 414 / 414 | 132.31 | 160.02 | 43.02 | 74.53 | 0 |
| 16 | 789 / 789 | 139.14 | 266.50 | 44.82 | 142.56 | 0 |
| 32 | 1,082 / 1,244 | 221.37 | 1,262.50 | 60.01 | 233.10 | 0 |
| 64 | 110 / 1,332 | 5,508.65 | 8,839.95 | 72.64 | 215.48 | 0 |

TTFT is the time to the first text or tool-call chunk. Chunk gap estimates the interval between chunks from first output to stream completion, summarized as the median across requests with at least two chunks. [Metric definitions](../analysis/summarize.py)

![vLLM p90 time to first output rises above the one-second target at 32 users](../results/baseline%20%28vLLM%29/p90_ttft.png)

**Profile the 32-user load first.** From 16 to 32 users, throughput rose from 142.56 to 233.10 streamed chunks/s, but the share of requests receiving output within a second fell from 100% to 87%. [Engine comparison](08-engine-comparison.md)
