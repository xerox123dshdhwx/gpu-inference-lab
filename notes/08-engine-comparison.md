# Engine comparison

## Setup

Both runs were recorded on November 21, 2026. They served `google/gemma-4-E4B-it` with a 16,384-token context on one NVIDIA L4 (`g6.xlarge`) in the `gpu-lab` EKS cluster in Paris.

Both used the same streamed agent workload with tool definitions enabled. The benchmark warmed up for 60 seconds with four users, then ran each of the seven load levels for 180 seconds. Each request had a 300-token output limit.

- **vLLM** ran `vllm/vllm-openai:v0.33.0` with `--max-num-seqs=80`, `--max-num-batched-tokens=1024` and chunked prefill enabled.
- **SGLang** ran `lmsysorg/sglang:latest` with `--mem-fraction-static=0.80` to make room for the KV cache at startup. SGLang chose its request concurrency automatically.

Both deployments used the `gemma4` tool-call parser. Details are in the [vLLM manifest](../k8s/vllm.yaml) and the [SGLang manifest](../k8s/sglang.yaml).

## Results

The target is a p90 time to first token below 1,000 ms. Capacity at target is the highest tested load that meets this threshold.

The benchmark estimates inter-token latency (ITL) from the mean interval between streaming chunks within each request, then takes the median across requests. The throughput column reports streaming chunks per second.

### vLLM

| Users | p50 TTFT (ms) | p90 TTFT (ms) | ITL (ms) | Chunks/s | Errors |
|---:|---:|---:|---:|---:|---:|
| 1 | 67.54 | 77.07 | 40.74 | 11.95 | 0 |
| 2 | 70.93 | 138.11 | 41.51 | 19.63 | 0 |
| 4 | 127.12 | 151.26 | 42.21 | 41.37 | 0 |
| 8 | 132.31 | 160.02 | 43.02 | 74.53 | 0 |
| 16 | 139.14 | 266.50 | 44.82 | 142.56 | 0 |
| 32 | 221.37 | 1,262.50 | 60.01 | 233.10 | 0 |
| 64 | 5,508.65 | 8,839.95 | 72.64 | 215.48 | 0 |

**Highest tested load under 1 s p90 TTFT** — 16 users. [Raw results](../results/baseline/) · [p90 chart](../results/baseline/p90_ttft.png)

### SGLang

| Users | p50 TTFT (ms) | p90 TTFT (ms) | ITL (ms) | Chunks/s | Errors |
|---:|---:|---:|---:|---:|---:|
| 1 | 82.65 | 96.30 | 41.02 | 11.30 | 0 |
| 2 | 110.78 | 163.99 | 41.98 | 22.99 | 0 |
| 4 | 138.22 | 166.16 | 43.69 | 38.83 | 0 |
| 8 | 147.88 | 200.49 | 46.82 | 76.29 | 0 |
| 16 | 153.87 | 211.58 | 53.41 | 126.05 | 0 |
| 32 | 171.01 | 229.90 | 70.18 | 230.29 | 0 |
| 64 | 188.31 | 264.19 | 97.21 | 374.52 | 0 |

**Highest tested load under 1 s p90 TTFT** — 64 users, the top load in this sweep. [Raw results](../results/sglang/) · [p90 chart](../results/sglang/p90_ttft.png)

### Tool calls

vLLM scored **65% exact match (130/200)** in the separate quality evaluation. The SGLang smoke test returned a structured `get_weather` call with `{"city":"Paris"}`. The 200-case evaluation ran on vLLM. [vLLM quality result](../results/baseline/quality.txt)

## Findings

vLLM had lower p90 TTFT from one to eight users. SGLang had lower p90 TTFT at 16, 32 and 64 users. At 64 users, SGLang started responding in 264 ms at p90 and vLLM took 8.84 s. At that load, the measured median streaming chunk interval was 97.21 ms for SGLang and 72.64 ms for vLLM.

## Limits

The measurements describe these two configurations on one L4. They include the effects of the vLLM batch token budget and the SGLang memory allocation. The exact SGLang build and startup KV cache sizes were unavailable in the saved run artifacts.
