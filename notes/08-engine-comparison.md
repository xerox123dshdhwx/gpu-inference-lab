# Engine comparison

## Setup

All three runs were recorded on November 21, 2026, on one NVIDIA L4 (`g6.xlarge`) in the `gpu-lab` EKS cluster in Paris. vLLM and SGLang served `google/gemma-4-E4B-it` with a 16,384-token context. llama.cpp served the Q8_0 GGUF build of the same model.

All three used the same streamed agent workload with tool definitions enabled. The benchmark warmed up for 60 seconds with four users, then ran each of the seven load levels for 180 seconds. Each request had a 300-token output limit.

- **vLLM** ran `vllm/vllm-openai:v0.33.0` with `--max-num-seqs=80`, `--max-num-batched-tokens=1024` and chunked prefill enabled.
- **SGLang** ran `lmsysorg/sglang:latest` with `--mem-fraction-static=0.80` to make room for the KV cache at startup. SGLang chose its request concurrency automatically.
- **llama.cpp** ran `ghcr.io/ggml-org/llama.cpp:server-cuda` (build `b12602-418fe97b5`) with `--reasoning off`, `--jinja`, `-ngl 999`, `-np 16` and `-c 131072`. [llama.cpp manifest](../k8s/llamacpp.yaml)

vLLM and SGLang used the `gemma4` tool-call parser. [vLLM manifest](../k8s/vllm.yaml) · [SGLang manifest](../k8s/sglang.yaml)

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

### llama.cpp

| Users | p50 TTFT (ms) | p90 TTFT (ms) | ITL (ms) | Chunks/s | Errors |
|---:|---:|---:|---:|---:|---:|
| 1 | 110.32 | 120.96 | 24.31 | 13.81 | 0 |
| 2 | 125.96 | 196.76 | 25.38 | 27.81 | 0 |
| 4 | 183.77 | 302.60 | 33.15 | 45.09 | 0 |
| 8 | 340.90 | 492.20 | 69.58 | 63.79 | 0 |
| 16 | 571.20 | 788.37 | 126.82 | 75.97 | 0 |
| 32 | 2,729.40 | 3,705.54 | 96.83 | 134.85 | 0 |
| 64 | 11,732.82 | 12,947.98 | 97.50 | 139.75 | 0 |

**Highest tested load under 1 s p90 TTFT** — 16 users. All 2,740 measured requests produced at least one text or tool-call chunk, so each TTFT measures observed output. [Raw results](../results/llamacpp/) · [p90 chart](../results/llamacpp/p90_ttft.png)

In the earlier run with the default thinking setting, 1,053 of 1,222 requests produced no counted output. Replaying one of those prompts showed that reasoning exhausted its 300-token budget. With thinking disabled, the same prompt returned text in 27 tokens. [Replay code](../workload/replay.py)

### Tool calls

vLLM scored **65% exact match (130/200)** in the separate quality evaluation. The SGLang smoke test returned a structured `get_weather` call with `{"city":"Paris"}`. The 200-case evaluation ran on vLLM, and the llama.cpp run had it disabled. [vLLM quality result](../results/baseline/quality.txt)

## Findings

vLLM had the lowest p90 TTFT from one to eight users. SGLang had the lowest p90 TTFT at 16, 32 and 64 users. At 64 users, p90 TTFT was 264 ms for SGLang, 8.84 s for vLLM and 12.95 s for llama.cpp. At that load, the median streaming chunk interval was 97.21 ms for SGLang, 72.64 ms for vLLM and 97.50 ms for llama.cpp.

## Limits

The measurements describe these configurations on one L4, including the vLLM batch token budget, the SGLang memory allocation and the llama.cpp GGUF quantization and slot settings. The exact SGLang build and startup KV cache sizes were unavailable in the saved run artifacts.
