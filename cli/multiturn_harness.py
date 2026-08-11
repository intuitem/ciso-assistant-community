"""Multi-turn tool-selection under accumulated tool output.

The single-turn harness never exercised A3: each call started from an empty
context. Here the model's own tool results are fed back, so turn N sees every
prior response. Run with bounding on (default) and off (env overrides) to
measure whether response bloat degrades later turns.

  # bounded (current defaults)
  LM_API_TOKEN=... uv run python multiturn.py --models qwen/qwen3-4b-2507

  # unbounded (pre-A3 behaviour)
  CA_MCP_PAGE_LIMIT=10000 CA_MCP_MAX_ITEMS=100000 \
  CA_MCP_MAX_RESPONSE_CHARS=100000000 LM_API_TOKEN=... \
  uv run python multiturn.py --models qwen/qwen3-4b-2507
"""

import argparse
import asyncio
import json
import os
import sys
import requests

BASE = os.environ.get("LM_BASE", "http://127.0.0.1:1234/v1")
TOKEN = os.environ.get("LM_API_TOKEN", "")
CLI_DIR = os.environ.get("CA_CLI_DIR", os.path.dirname(os.path.abspath(__file__)))

# Turn 1 of each conversation is deliberately the heaviest read available, so
# later turns are answered with a context already full of tool output.
CONVERSATIONS = [
    [
        ("Show me our vulnerabilities", {"get_vulnerabilities"}),
        ("Now list the domains", {"get_folders"}),
        (
            "And which compliance frameworks are loaded?",
            {"get_frameworks", "get_loaded_libraries"},
        ),
        ("Finally, show me the assets", {"get_assets"}),
    ],
    [
        ("List all risk scenarios", {"get_risk_scenarios"}),
        ("Now show the applied controls", {"get_applied_controls"}),
        ("What third-party entities do we work with?", {"get_entities"}),
        ("Show me the security exceptions", {"get_security_exceptions"}),
    ],
]

SYSTEM = (
    "You are a GRC assistant with access to the CISO Assistant platform. "
    "Use the provided tools to answer the user's question. Call exactly one tool."
)


def load_tools_and_fns():
    if CLI_DIR not in sys.path:
        sys.path.insert(0, CLI_DIR)
    from mcp.server.fastmcp import FastMCP
    from ca_mcp.server import READ_TOOLS

    probe = FastMCP("probe")
    for fn in READ_TOOLS:
        probe.tool()(fn)
    tools = asyncio.run(probe.list_tools())
    specs = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": (t.description or "")[:1024],
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]
    return specs, {fn.__name__: fn for fn in READ_TOOLS}


def chat(model, messages, tools, timeout=300):
    r = requests.post(
        f"{BASE}/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0,
            "max_tokens": 512,
        },
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    args = ap.parse_args()
    if not TOKEN:
        sys.exit("LM_API_TOKEN not set")

    specs, fns = load_tools_and_fns()

    for model in args.models.split(","):
        model = model.strip()
        hits = total = 0
        ctx_chars = 0
        print(f"\n{model}", flush=True)
        for ci, convo in enumerate(CONVERSATIONS):
            messages = [{"role": "system", "content": SYSTEM}]
            for ti, (prompt, expected) in enumerate(convo):
                messages.append({"role": "user", "content": prompt})
                total += 1
                # A failure on one turn must not abandon the remaining turns,
                # conversations and models.
                try:
                    d = chat(model, messages, specs)
                    msg = d["choices"][0]["message"]
                    calls = msg.get("tool_calls") or []
                except Exception as e:
                    print(f"  c{ci} t{ti}: ERROR {type(e).__name__}", flush=True)
                    messages.append({"role": "assistant", "content": ""})
                    continue
                if not calls:
                    print(
                        f"  c{ci} t{ti}: NO TOOL CALL           want {sorted(expected)[0]}",
                        flush=True,
                    )
                    messages.append(
                        {"role": "assistant", "content": msg.get("content") or ""}
                    )
                    continue
                name = calls[0]["function"]["name"]
                # SYSTEM asks for exactly one call. Counting a hit on calls[0]
                # alone would score a scattergun response as correct whenever the
                # first pick happens to match, inflating measured accuracy.
                ok = len(calls) == 1 and name in expected
                hits += ok
                # Execute EVERY emitted call with its own arguments and reply to
                # each id. Tools like count_objects(object_type) are required-arg,
                # so invoking them bare raised TypeError and fed the model an
                # error string instead of real output.
                messages.append({"role": "assistant", "tool_calls": calls})
                payload = ""
                for call in calls:
                    cname = call["function"]["name"]
                    try:
                        cargs = json.loads(call["function"].get("arguments") or "{}")
                        if not isinstance(cargs, dict):
                            raise ValueError("arguments must be an object")
                    except Exception:
                        cargs = {}
                    try:
                        result = (
                            asyncio.run(fns[cname](**cargs))
                            if cname in fns
                            else "(unavailable)"
                        )
                    except Exception as e:
                        result = f"(tool error: {type(e).__name__}: {e})"
                    ctx_chars += len(result)
                    if cname == name:
                        payload = result
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id", "0"),
                            "content": result,
                        }
                    )
                mark = "ok " if ok else ("MULTI" if len(calls) > 1 else "WRONG")
                print(
                    f"  c{ci} t{ti}: {mark} {name:<28} result {len(payload):>7} chars"
                    + (f"  [{len(calls)} calls]" if len(calls) > 1 else "")
                    + ("" if ok else f"  want {sorted(expected)[0]}"),
                    flush=True,
                )
        print(
            f"  => {hits}/{total} correct | total tool output fed back: "
            f"{ctx_chars:,} chars (~{ctx_chars // 4:,} tokens)",
            flush=True,
        )


if __name__ == "__main__":
    main()
