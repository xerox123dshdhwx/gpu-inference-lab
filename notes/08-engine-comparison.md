# Engine comparison: vLLM, SGLang and llama.cpp

## Setup

All three runs were recorded on November 21, 2026, on one NVIDIA L4 (`g6.xlarge`) in the `gpu-lab` EKS cluster in Paris. vLLM and SGLang used the BF16 Gemma 4 E4B instruction-tuned checkpoint with a 16,384-token context limit. llama.cpp served the Q8_0 GGUF build of the same model. [Gemma model configuration](https://huggingface.co/google/gemma-4-E4B-it/blob/main/config.json) · [GGUF model](https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF)

All three used the same streamed agent workload with tool definitions enabled. The benchmark warmed up for 60 seconds with four users, then ran each of the seven load levels for 180 seconds. Each request had a 300-token output limit.

- **vLLM** ran `vllm/vllm-openai:v0.33.0` with `--max-num-seqs=80`, `--max-num-batched-tokens=1024` and chunked prefill enabled.
- **SGLang** ran `lmsysorg/sglang:latest` with `--mem-fraction-static=0.80`. The saved record identifies the image tag only. SGLang chose its request concurrency automatically.
- **llama.cpp** ran `ghcr.io/ggml-org/llama.cpp:server-cuda` (build `b12602-418fe97b5`) with `--reasoning off`, `--jinja`, `-ngl 999`, `-np 16` and `-c 131072`. [llama.cpp manifest](../k8s/llamacpp.yaml)

vLLM and SGLang used the `gemma4` tool-call parser. [vLLM manifest](../k8s/vllm.yaml) · [SGLang manifest](../k8s/sglang.yaml)

## Results

The target is a p90 time to first token (TTFT) below 1,000 ms. The client starts the clock when it sends a request and stops it at the first chunk containing text or a tool call. Capacity is the highest **tested** load that meets the target.

| Engine | KV cache capacity (tokens) | p90 TTFT, 1 user | p90 TTFT, 16 users | Streamed chunks/s, 16 users | Users at p90 < 1 s |
|---|---|---:|---:|---:|---:|
| vLLM | Unrecorded for this run | 77.07 ms | 266.50 ms | 142.56 | 16 |
| SGLang | Unrecorded for this run | 96.30 ms | 211.58 ms | 126.05 | 64 |
| llama.cpp | 131,072 configured context tokens across 16 slots | 120.96 ms | 788.37 ms | 75.97 | 16 |

The replay recorded streaming chunks and omitted completion-token counts. Although the summary script names this rate `tokens_per_s`, the saved files support only chunks/s. The llama.cpp token budget comes from its manifest. The corresponding startup allocation for each engine could not be verified for these runs. [Replay client](../workload/replay.py) · [Summary calculation](../analysis/summarize.py) · [llama.cpp manifest](../k8s/llamacpp.yaml)

![p90 TTFT against simultaneous users for vLLM, SGLang and llama.cpp, with a 1-second target](../results/compare_baseline_vs_sglang_vs_llamacpp.png)

The chart labels vLLM as `baseline (vLLM)`. It reached 16 users under target and crossed 1 second at 32 users. SGLang stayed below target through 64 users, the highest load tested.

## What each engine does differently

- **vLLM (PagedAttention).** vLLM stores attention keys and values in fixed-size blocks and allocates more blocks as a sequence grows. A block table lets attention read a sequence whose blocks occupy different physical locations in GPU memory. vLLM had the lowest p90 TTFT at every tested load from one to eight users. [PagedAttention paper](https://arxiv.org/abs/2309.06180)
- **SGLang (RadixAttention).** SGLang indexes cached token sequences in a radix tree. When a new prompt shares a prefix with a cached prompt, the engine can reuse the keys and values for that prefix and process only the remaining tokens. The workload repeats a system prompt and tool definitions, and SGLang reached 264.19 ms p90 at 64 users. The run did not record prefix-cache hits. [RadixAttention design](https://www.lmsys.org/blog/2024-01-17-sglang/)
- **llama.cpp (parallel slots and GGUF).** The server loaded Q8_0-quantized weights from GGUF and exposed 16 parallel request slots. When all slots are busy, another request must wait for one to become available. From 16 to 32 simulated users, p90 TTFT rose from 788.37 ms to 3,705.54 ms. [llama.cpp server documentation for this build](https://github.com/ggml-org/llama.cpp/blob/418fe97b5/tools/server/README.md)

## Limits

This comparison covers one model, one GPU type and loads up to 64 users with the settings listed above. Weight precision, context budgets, vLLM's batch token budget, SGLang's memory fraction and llama.cpp's slot limit can all affect the results. Only vLLM has a 200-case tool-call quality score, so equal output quality across engines remains unverified. [Quality result](../results/baseline%20(vLLM)/quality.txt)

## Decision

Use **vLLM for weeks 3–5**. At 16 users it met the target with 266.50 ms p90 TTFT and delivered the highest measured chunk throughput of the three. SGLang is the stronger choice on this workload if the sole criterion is capacity under one second. The next experiments tune vLLM and use llm-d routing, which selects vLLM as its default model server. KServe’s Hugging Face runtime also defaults to vLLM for supported models, and AWS’s EKS inference guide demonstrates a vLLM deployment. [llm-d model servers](https://llm-d.ai/docs/architecture/model-servers) · [KServe runtime overview](https://kserve.github.io/website/docs/model-serving/generative-inference/overview) · [AWS EKS inference guide](https://docs.aws.amazon.com/eks/latest/userguide/ml-inference-load-serve-model.html)

## Per-load measurements

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

**Highest tested load under 1 s p90 TTFT** — 16 users. [Raw results](../results/baseline%20(vLLM)/) · [p90 chart](../results/baseline%20(vLLM)/p90_ttft.png)

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

vLLM scored **65% exact match (130/200)** in the separate quality evaluation. The SGLang smoke test returned a structured `get_weather` call with `{"city":"Paris"}`. The 200-case evaluation ran on vLLM, and the llama.cpp run had it disabled. [vLLM quality result](../results/baseline%20(vLLM)/quality.txt)
