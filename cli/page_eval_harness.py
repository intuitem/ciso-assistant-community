"""Score the in-app chat on typical questions asked from the main pages (evals/page_questions.json).

Each question is sent through the chat with the page context the frontend would send
({path, model, title}), against an instance seeded with `manage.py seed_demo`. The model
is the backend's chat setting; --label only names the run.
Claude (the `claude` CLI) judges every answer against the golden answer, fact by fact.

  TOKEN=<CISO Assistant token> python page_eval_harness.py --label qwen3-4b \\
      --chat-url http://127.0.0.1:8000/api --backend-log backend.log --results page-qwen3-4b.jsonl
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from framework_eval_harness import answer_chat

QUESTIONS = Path(__file__).parent / "evals/page_questions.json"

JUDGE = """You grade an assistant's answer against a golden answer written from the actual data.

Question (asked from the page {page}): {question}
Golden answer: {golden}
Facts to check:
{facts}

Assistant's answer:
<answer>
{answer}
</answer>

For each fact, decide whether the answer states it (paraphrase and different formatting are fine;
a fact like "no other X is listed" holds only if the answer lists nothing beyond the golden items).
Then say whether the answer asserts anything that contradicts the golden answer.
Reply with only this JSON: {{"facts": [true/false per fact, in order], "contradiction": true/false, "note": "<one short sentence>"}}"""


def claude_text(prompt, model, system, timeout=300):
    """One `claude -p` call with a bare context (no settings, MCP, skills or
    project files): ~200x cheaper per call than the default context."""
    out = subprocess.run(
        [
            "claude",
            "-p",
            "--model",
            model,
            "--output-format",
            "json",
            "--tools",
            "",
            "--no-session-persistence",
            "--setting-sources",
            "",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--system-prompt",
            system,
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
        cwd=tempfile.gettempdir(),
    )
    return json.loads(out.stdout)["result"]


def judge(q, answer, model):
    prompt = JUDGE.format(
        page=q["page"],
        question=q["question"],
        golden=q["golden"],
        facts="\n".join(f"{i}. {f}" for i, f in enumerate(q["facts"], 1)),
        answer=answer,
    )
    text = claude_text(prompt, model, "You are a strict grader. Reply with JSON only.")
    verdict = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    assert len(verdict["facts"]) == len(q["facts"]), "judge returned a wrong fact count"
    return verdict


def resolve_path(q, url, headers):
    """The page path; detail pages are looked up by ref_id (or name) since seeded ids differ per instance."""
    obj = q.get("object")
    if not obj:
        return q["page"]
    key = "ref_id" if obj.get("ref_id") else "name"
    res = requests.get(
        f"{url}/{obj['api']}/", params={key: obj[key]}, headers=headers, timeout=30
    )
    res.raise_for_status()
    (hit,) = [r for r in res.json()["results"] if r.get(key) == obj[key]]
    return f"{q['page']}/{hit['id']}"


def score(verdict):
    """Share of facts stated; a contradiction caps the answer at half."""
    s = sum(verdict["facts"]) / len(verdict["facts"])
    return min(s, 0.5) if verdict["contradiction"] else s


def run_one(q, args, headers):
    trace, verdict, text, err = [], None, "", None
    try:
        q = {
            **q,
            "lang": "fr" if q.get("variant") == "fr" else "en",
            "page_context": {
                "path": resolve_path(q, args.chat_url, headers),
                "title": q["title"],
            },
        }
        text, _ = answer_chat(q, args.chat_url, args.backend_log, trace)
        verdict = judge(q, text, args.judge_model)
        s = score(verdict)
    except Exception as e:
        # one failure must not abandon the rest of the run
        s, err = 0.0, f"{type(e).__name__}: {e}"[:160]
    return {
        "label": args.label,
        "id": q["id"],
        "base_id": q.get("base_id", q["id"]),
        "variant": q.get("variant", "en"),
        "page": q["page"].strip("/"),
        "page_context": q.get("page_context"),
        "question": q["question"],
        "score": s,
        "error": err,
        "verdict": verdict,
        "trace": trace,
        "answer": text,
        "golden": q["golden"],
    }


def summary(rows, key):
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r["score"])
    for name, xs in sorted(groups.items()):
        print(f"  => {name:<24} {sum(xs) / len(xs):>5.0%}  ({sum(xs):.1f}/{len(xs)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--label", required=True, help="names the run (the model is the backend's)"
    )
    ap.add_argument(
        "--chat-url", required=True, help="backend API, e.g. http://127.0.0.1:8000/api"
    )
    ap.add_argument(
        "--backend-log", help="backend log, to record the tool the chat chose"
    )
    ap.add_argument("--questions", default=str(QUESTIONS), help="questions JSON file")
    ap.add_argument("--judge-model", default="sonnet", help="model for `claude -p`")
    ap.add_argument("--only", help="comma-separated question ids")
    ap.add_argument("--workers", type=int, default=1, help="questions asked at once")
    ap.add_argument("--results", help="write per-question results JSONL here")
    args = ap.parse_args()

    qs = json.loads(Path(args.questions).read_text(encoding="utf-8"))["questions"]
    if args.only:
        qs = [q for q in qs if q["id"] in args.only.split(",")]
    headers = {"Authorization": f"Token {os.environ['TOKEN']}"}
    out = open(args.results, "w", encoding="utf-8") if args.results else None
    rows = []
    print(f"{args.label}: {len(qs)} page questions", flush=True)
    with ThreadPoolExecutor(args.workers) as pool:
        for r in pool.map(lambda q: run_one(q, args, headers), qs):
            rows.append(r)
            note = (r["verdict"] or {}).get("note") or r["error"] or ""
            print(f"  {r['score']:4.2f} {r['id']:<40} {note}"[:200], flush=True)
            if out:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush()
    summary(rows, "page")
    if len({r["variant"] for r in rows}) > 1:
        summary(rows, "variant")
    print(
        f"  => {'all':<24} {sum(r['score'] for r in rows) / len(rows):>5.0%}  "
        f"({sum(r['score'] for r in rows):.1f}/{len(rows)})"
    )
    if out:
        out.close()


if __name__ == "__main__":
    assert score({"facts": [True, False], "contradiction": False}) == 0.5
    assert score({"facts": [True, True], "contradiction": True}) == 0.5
    main()
