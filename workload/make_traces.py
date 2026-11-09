"""Build the quality-check set and the agent conversations from xLAM."""
import json
import random
from datasets import load_dataset

random.seed(0)
ds = load_dataset("Salesforce/xlam-function-calling-60k", split="train")
TYPES = {"int": "integer", "float": "number", "bool": "boolean", "list": "array", "dict": "object"}


def to_openai_tool(tool):
    """xLAM describes tools in its own format; convert to the OpenAI format the engines expect."""
    props, required = {}, []
    for name, p in tool.get("parameters", {}).items():
        raw = str(p.get("type", "str")).lower()
        base = raw.split(",")[0].split("[")[0].strip()
        props[name] = {"type": TYPES.get(base, "string"), "description": p.get("description", "")}
        if "optional" not in raw:
            required.append(name)
    return {"type": "function", "function": {
        "name": tool["name"], "description": tool.get("description", ""),
        "parameters": {"type": "object", "properties": props, "required": required}}}


rows = [ds[i] for i in random.sample(range(len(ds)), 1200)]

# Part 1. Quality check: 200 questions, each with its own tools and the known correct calls
with open("eval/eval_set.jsonl", "w") as f:
    for r in rows[:200]:
        f.write(json.dumps({
            "query": r["query"],
            "tools": [to_openai_tool(t) for t in json.loads(r["tools"])],
            "answers": json.loads(r["answers"]),
        }) + "\n")

# Part 2. Agent conversations: one system prompt and 12 tools, stored once, plus 150 conversations
tools = {}
for r in rows[200:260]:
    for t in json.loads(r["tools"]):
        tools.setdefault(t["name"], to_openai_tool(t))
questions = [r["query"] for r in rows[200:]]
with open("workload/traces.json", "w") as f:
    json.dump({
        "system": open("workload/system_prompt.txt").read(),
        "tools": list(tools.values())[:12],
        "conversations": [random.sample(questions, random.randint(3, 8)) for _ in range(150)],
    }, f)
print("Wrote eval/eval_set.jsonl and workload/traces.json")