"""Score tool calls: exact match on function names and arguments."""
import json
import os
import sys
from openai import OpenAI

client = OpenAI(base_url=sys.argv[1].rstrip("/") + "/v1", api_key=os.environ.get("API_KEY", "none"))
MODEL = os.environ.get("MODEL", "google/gemma-4-E4B-it")
EVAL_SET = os.environ.get("EVAL_SET", "eval/eval_set.jsonl")


def norm(calls):
    return sorted((c["name"], json.dumps(c["arguments"], sort_keys=True)) for c in calls)


ok = total = 0
for line in open(EVAL_SET):
    ex = json.loads(line)
    total += 1
    try:
        resp = client.chat.completions.create(
            model=MODEL, temperature=0, tools=ex["tools"], tool_choice="auto",
            messages=[{"role": "user", "content": ex["query"]}])
        calls = resp.choices[0].message.tool_calls or []
        got = [{"name": c.function.name, "arguments": json.loads(c.function.arguments or "{}")}
               for c in calls]
        ok += norm(got) == norm(ex["answers"])
    except Exception:
        pass  # a broken call counts as wrong
print(f"Tool-call exact match: {ok}/{total} = {ok / total:.1%}")