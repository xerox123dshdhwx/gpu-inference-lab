"""Replay agent conversations: USERS simultaneous users for DURATION seconds."""
import asyncio
import json
import os
import random
import sys
import time
from openai import AsyncOpenAI

URL, USERS, DURATION, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
MODEL = os.environ.get("MODEL", "google/gemma-4-E4B-it")
TRACES = json.load(open(os.environ.get("TRACES", "workload/traces.json")))
USE_TOOLS = os.environ.get("TOOLS", "on") == "on"
LAYOUT = os.environ.get("LAYOUT", "good")  # "bad" is used in evening 10
random.seed(0)
client = AsyncOpenAI(base_url=URL.rstrip("/") + "/v1",
                     api_key=os.environ.get("API_KEY", "none"), timeout=600)
records = []


def system_prompt():
    if LAYOUT == "bad":  # a changing first line breaks prefix caching
        return f"Current time: {time.time()}\n" + TRACES["system"]
    return TRACES["system"]


def tool_args():
    if not USE_TOOLS:
        return {}
    tools = list(TRACES["tools"])
    if LAYOUT == "bad":
        random.shuffle(tools)
    return {"tools": tools}


async def one_request(conv_id, turn, messages):
    start = time.perf_counter()
    first, chunks, text = None, 0, ""
    try:
        stream = await client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=300, temperature=0,
            stream=True, **tool_args())
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content or delta.tool_calls:
                if first is None:
                    first = time.perf_counter()
                chunks += 1
                text += delta.content or ""
        end = time.perf_counter()
        records.append({"conv": conv_id, "turn": turn, "start": start,
                        "ttft": (first or end) - start, "e2e": end - start, "chunks": chunks})
    except Exception as e:  # a failed request is recorded, not hidden
        records.append({"conv": conv_id, "turn": turn, "start": start, "error": str(e)[:200]})
    return text


async def conversation(conv_id):
    messages = [{"role": "system", "content": system_prompt()}]
    for i, question in enumerate(TRACES["conversations"][conv_id]):
        messages.append({"role": "user", "content": question})
        reply = await one_request(conv_id, i, messages)
        messages.append({"role": "assistant", "content": reply or "(called a tool)"})
        await asyncio.sleep(random.uniform(1, 3))  # the user reads and types


async def user(deadline):
    while time.perf_counter() < deadline:
        await conversation(random.randrange(len(TRACES["conversations"])))


async def main():
    deadline = time.perf_counter() + DURATION
    await asyncio.gather(*(user(deadline) for _ in range(USERS)))
    with open(OUT, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


asyncio.run(main())