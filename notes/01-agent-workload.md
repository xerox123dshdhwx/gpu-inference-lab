# Designing the agent workload

## Why

A helpdesk conversation sends the same instructions and tool definitions on every turn, while the user’s question and conversation history change. Building that traffic first gives every engine and optimization the same work to do. It also lets us measure how soon the user sees output and check whether the model selected the right tool.

## Expected behavior

The study plan predicted that shared instructions and tool definitions would make up most of a first-turn request. Later turns add conversation history. This makes the workload a candidate for a prefix-caching experiment.

## What the saved workload contains

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

These are character counts from the stored inputs before an engine applies its chat template and tokenizer. Each evaluation case has its own tool definitions and expected calls. Both sets are drawn from xLAM using a fixed sampling seed. [Trace builder](../workload/make_traces.py) · [Saved conversations](../workload/traces.json) · [Evaluation cases](../eval/eval_set.jsonl)

## What the measurement tells us

Even the longest first user message in the trace is only 338 characters. The reusable beginning therefore dominates the first turn by character count. How much prefill time it saves depends on the engine reusing that prefix, which requires a separate cache experiment.

The replay samples these conversations with replacement. Each simulated user sends one request at a time, carries the previous messages forward, and waits 1–3 seconds between turns. The client counts streamed text and tool-call chunks. The quality evaluator separately compares function names and arguments against the answer key. [Replay client](../workload/replay.py) · [Tool-call evaluator](../eval/tool_eval.py)

## Decision

Use the checked-in trace and evaluation set for subsequent runs. Keep the system message and tool order fixed for the baseline so that changing prompt layout later is a deliberate experiment. [First vLLM baseline](05-baseline.md)
