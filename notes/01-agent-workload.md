# Agent workload

The replay samples scripted conversations built from xLAM function-calling questions. Each simulated user sends one request at a time, with 1–3 seconds between turns. Every request carries the same system instructions and tool definitions, followed by that user’s conversation history. The fixed prefix lets us measure how much work an engine can reuse across requests. [Replay client](../workload/replay.py)

| Measurement | Value |
| :--- | ---: |
| Scripted conversations | 150 |
| User turns in the trace | 829 |
| Turns per conversation | 3–8, median 6 |
| Shared system message | 5,860 characters |
| Shared tool definitions | 12 tools, 6,386 characters as compact JSON |
| Shared instructions and tools combined | 12,246 characters |
| Median first user message | 88.5 characters |
| Separate tool-call evaluation | 200 cases |

The shared prefix is larger than even the longest first user message (338 characters). The replay keeps the prefix and tool order fixed across engines. Lengths above describe the stored text before tokenization. [Saved conversations](../workload/traces.json) · [xLAM sampling and trace construction](../workload/make_traces.py)

Tool definitions travel with each request. The replay times model responses and leaves external tool execution out of the workload. A separate evaluation checks tool names and arguments against the expected calls for each case. [Evaluation cases](../eval/eval_set.jsonl) · [Scoring](../eval/tool_eval.py)
