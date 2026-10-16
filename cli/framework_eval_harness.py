"""Score a model on the framework-knowledge set (evals/framework_questions.jsonl).

  closed  the model answers from its weights alone: what fine-tuning would have to teach
  tools   the model may call the read-only MCP tools against a live instance; only
          frameworks loaded there can be answered
  chat    the question goes through the app's chat (/api/chat/sessions/.../message/);
          the model is the backend's chat setting, --models is only a label

Same scoring for both modes, on the final answer text:
  reverse  expected ref_id present
  mapping  recall of expected ref_ids (exact = all of them)
  lookup   approximate: share of the expected name's words present (>= 0.6 counts)

  LM_API_TOKEN=... uv run python framework_eval_harness.py --models qwen/qwen3-8b --sample 100
  LM_API_TOKEN=... CISO_ASSISTANT_... uv run python framework_eval_harness.py --models qwen/qwen3-8b --mode tools
  TOKEN=<CISO Assistant token> uv run python framework_eval_harness.py --models qwen3-4b --mode chat \
      --chat-url http://127.0.0.1:8000/api --backend-log backend.log
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
from pathlib import Path

import requests

from multiturn_harness import BASE, TOKEN, load_tools_and_fns

QUESTIONS = Path(__file__).parent / "evals/framework_questions.jsonl"

SYSTEM = {
    "closed": (
        "You are a GRC expert. Answer from your own knowledge, concisely. "
        "Always cite requirement references (ref ids) exactly as the framework writes them."
    ),
    "tools": (
        "You are a GRC assistant with access to the CISO Assistant platform. "
        "Look requirements up with the tools before answering: find_requirements for a "
        "requirement by reference or title, get_requirement_mappings (the requirement's "
        "framework and ref_id, plus the target framework) for its mappings, and report "
        "every mapped requirement, not a sample. "
        "Answer concisely and cite requirement references (ref ids) exactly."
    ),
}

# frameworks a general model has most likely seen; everything else is the long tail
MAINSTREAM = {
    f"urn:intuitem:risk:framework:{f}"
    for f in [
        "iso27001-2022",
        "iso27001-2013",
        "nist-csf-2.0",
        "nist-csf-1.1",
        "nist-sp-800-53-rev5",
        "soc2-2017",
        "soc2-2017-rev-2022",
        "pcidss-4_0",
        "nis2-directive",
        "dora",
        "gdpr",
    ]
}

STOPWORDS = set(
    "a an and the of to for in on with by or is are be as at from that this its it "
    "de la le les des du et en un une pour par sur au aux".split()
)


def ref_present(ref, text):
    # "4.1" must not match inside "4.10" or "14.1"; trailing sentence dot is fine
    pat = rf"(?<![\w.]){re.escape(ref)}(?![\w]|\.\w)"
    return re.search(pat, text, re.IGNORECASE) is not None


def words(s):
    return {w for w in re.findall(r"\w+", (s or "").lower()) if w not in STOPWORDS}


def score(q, answer):
    """Return a 0..1 score for one answer."""
    exp = q["expected"]
    if q["kind"] == "reverse":
        return float(ref_present(exp["ref_id"], answer))
    if q["kind"] == "mapping":
        refs = exp["ref_ids"]
        return sum(ref_present(r, answer) for r in refs) / len(refs)
    # shortcut: word overlap on the name (description when unnamed); upgrade to an
    # LLM judge if paraphrased-but-right answers get scored as misses
    want = words(exp.get("name") or exp.get("description"))
    got = words(answer)
    return 1.0 if want and len(want & got) / len(want) >= 0.6 else 0.0


def complete(
    model, messages, tools=None, max_tokens=8192, reasoning="none", timeout=600
):
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if reasoning:
        # LM Studio honours this one; chat_template_kwargs.enable_thinking is ignored
        body["reasoning_effort"] = reasoning
    if tools:
        body |= {"tools": tools, "tool_choice": "auto"}
    r = requests.post(
        f"{BASE}/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=timeout,
    )
    r.raise_for_status()
    choice = r.json()["choices"][0]
    return choice["message"], choice.get("finish_reason")


def run_tools(fns, calls, messages, trace):
    messages.append({"role": "assistant", "tool_calls": calls})
    for call in calls:
        name = call["function"]["name"]
        trace.append([name, call["function"].get("arguments")])
        try:
            args = json.loads(call["function"].get("arguments") or "{}")
            result = asyncio.run(fns[name](**args)) if name in fns else "(unavailable)"
        except Exception as e:
            result = f"(tool error: {type(e).__name__}: {e})"
        messages.append(
            {"role": "tool", "tool_call_id": call.get("id", "0"), "content": result}
        )


class EmptyAnswer(Exception):
    """No final text: reasoning ate the token budget, or tool rounds ran out."""


def answer_chat(q, url, log, trace):
    """Ask through the app's chat (one session per question); the model is the backend's setting."""
    h = {
        "Authorization": f"Token {os.environ['TOKEN']}",
        # the chat answers in the browser's language
        "Accept-Language": q.get("lang", "en"),
    }
    sid = requests.post(f"{url}/chat/sessions/", json={}, headers=h, timeout=30)
    sid.raise_for_status()
    offset = Path(log).stat().st_size if log else 0
    r = requests.post(
        f"{url}/chat/sessions/{sid.json()['id']}/message/",
        json={
            "content": q["question"],
            **({"page_context": q["page_context"]} if q.get("page_context") else {}),
        },
        headers=h,
        stream=True,
        timeout=600,
    )
    r.raise_for_status()
    text = ""
    for line in r.iter_lines(decode_unicode=True):
        if not (line or "").startswith("data: "):
            continue
        ev = json.loads(line[6:])
        if ev.get("type") == "token":
            text += ev["content"]
        elif ev.get("type") == "error":
            raise RuntimeError(ev.get("content"))
    if log:
        with open(log, encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            plain = re.sub(r"\x1b\[[0-9;]*m", "", f.read())
        # this message's request id, so concurrent questions keep their own trace
        rid = re.search(
            rf"request='POST /api/chat/sessions/{sid.json()['id']}/message/' request_id=(\S+)",
            plain,
        )
        trace += [
            (name, args)
            for name, args, line_rid in re.findall(
                r"Tool call: (\w+)\((.*?)\) \[chat.*?request_id=(\S+)", plain
            )
            if rid and line_rid == rid.group(1)
        ]
    if not text.strip():
        raise EmptyAnswer("empty chat answer")
    return text.strip(), len(trace)


def answer(model, q, mode, specs, fns, max_steps, max_tokens, reasoning, trace):
    """Return (final answer text, number of tool calls made)."""
    messages = [
        {"role": "system", "content": SYSTEM[mode]},
        {"role": "user", "content": q["question"]},
    ]
    ncalls = 0
    for _ in range(max_steps):
        msg, finish = complete(model, messages, specs, max_tokens, reasoning)
        calls = msg.get("tool_calls") or []
        if not calls:
            text = msg.get("content") or ""
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
            if not text:
                raise EmptyAnswer(f"finish_reason={finish}")
            return text, ncalls
        ncalls += len(calls)
        run_tools(fns, calls, messages, trace)
    raise EmptyAnswer(f"no answer after {max_steps} tool rounds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--models", required=True, help="comma-separated LM Studio model ids"
    )
    ap.add_argument("--mode", default="closed", choices=["closed", "tools", "chat"])
    ap.add_argument("--kinds", default="lookup,reverse,mapping")
    ap.add_argument(
        "--slice",
        default="all",
        choices=["all", "mainstream", "longtail"],
        help="by the question's (source) framework",
    )
    ap.add_argument("--sample", type=int, help="random subset size (seeded)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-steps", type=int, default=5, help="tool rounds per question")
    ap.add_argument(
        "--max-tokens", type=int, default=8192, help="reasoning models need room"
    )
    ap.add_argument(
        "--reasoning-effort",
        default="none",
        help="none|low|medium|high; empty string leaves the model default",
    )
    ap.add_argument(
        "--tools", help="comma-separated tool names to offer (default: all read tools)"
    )
    ap.add_argument(
        "--chat-url", help="chat mode: backend API, e.g. http://127.0.0.1:8013/api"
    )
    ap.add_argument(
        "--backend-log", help="chat mode: backend log, to record the tool it chose"
    )
    ap.add_argument("--results", help="write per-question results JSONL here")
    args = ap.parse_args()
    if args.mode == "chat":
        if not os.environ.get("TOKEN") or not args.chat_url:
            sys.exit("chat mode needs TOKEN and --chat-url")
    elif not TOKEN:
        sys.exit("LM_API_TOKEN not set")

    kinds = set(args.kinds.split(","))
    qs = [
        q
        for q in map(
            json.loads, QUESTIONS.read_text(encoding="utf-8").split("\n")[:-1]
        )  # splitlines() breaks on U+2028 inside strings
        if q["kind"] in kinds
        and (
            args.slice == "all"
            or (q["framework_urn"] in MAINSTREAM) == (args.slice == "mainstream")
        )
    ]
    if args.sample:
        qs = random.Random(args.seed).sample(qs, min(args.sample, len(qs)))
    specs, fns = load_tools_and_fns() if args.mode == "tools" else (None, {})
    if specs and args.tools:
        keep = set(args.tools.split(","))
        specs = [s for s in specs if s["function"]["name"] in keep]
        assert {s["function"]["name"] for s in specs} == keep, "unknown tool name"

    out = open(args.results, "w", encoding="utf-8") if args.results else None
    for model in args.models.split(","):
        model = model.strip()
        print(f"\n{model} [{args.mode}/{args.slice}] {len(qs)} questions", flush=True)
        totals = {}
        for i, q in enumerate(qs):
            trace = []
            try:
                text, ncalls = (
                    answer_chat(q, args.chat_url, args.backend_log, trace)
                    if args.mode == "chat"
                    else answer(
                        model,
                        q,
                        args.mode,
                        specs,
                        fns,
                        args.max_steps,
                        args.max_tokens,
                        args.reasoning_effort,
                        trace,
                    )
                )
                s, err = score(q, text), None
            except Exception as e:
                # one failure must not abandon the rest of the run
                text, ncalls, s, err = "", 0, 0.0, f"{type(e).__name__}: {e}"[:120]
            t = totals.setdefault(q["kind"], [0.0, 0, 0])
            t[0] += s
            t[1] += 1
            t[2] += err is not None
            mark = "ok " if s == 1 else ("ERR" if err else f"{s:.1f}")
            print(
                f"  {i:>4} {mark} {q['id']:<14} {q['question'][:70]}"
                + (f"  [{err}]" if err else ""),
                flush=True,
            )
            if out:
                out.write(
                    json.dumps(
                        {
                            "model": model,
                            "mode": args.mode,
                            "id": q["id"],
                            "score": s,
                            "error": err,
                            "tool_calls": ncalls,
                            "trace": trace,
                            "answer": text,
                            "expected": q["expected"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        for kind, (s, n, errs) in sorted(totals.items()):
            print(f"  => {kind:<8} {s / n:>5.0%}  ({s:.1f}/{n}, {errs} errors)")
    if out:
        out.close()


if __name__ == "__main__":
    # scorer self-check: boundaries are where a ref_id match goes wrong
    assert ref_present("4.1", "See clause 4.1.")
    assert not ref_present("4.1", "See clause 4.10")
    assert not ref_present("4.1", "See 14.1")
    assert not ref_present("A.5.1", "A.5.12 covers it")
    assert ref_present("GV.OC-01", "maps to gv.oc-01, GV.OC-02")
    main()
