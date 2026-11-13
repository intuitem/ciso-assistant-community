"""Add natural rewordings of each page question: one English, one French.

The golden answer and facts are unchanged; only the wording varies, so the eval
measures how users phrase things rather than the generator's templates.
Claude writes the variants (`claude -p`, bare context).

  python paraphrase_questions.py evals/page_questions_large.json \\
      --out evals/page_questions_large_variants.json
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from page_eval_harness import claude_text

PROMPT = """Below are questions a user asks the chat assistant of a GRC tool (CISO Assistant)
while looking at a page. For each, write how a real user might type the same question:
- "en": a different English wording (casual, shorter or longer, any natural phrasing)
- "fr": a natural French wording, as a French-speaking CISO would type it (no calques)
Keep every proper noun, object name and reference (e.g. "RS.01", "A.5.15", "Kestrava Cloud B.V.")
exactly as written. Do not add or drop conditions: the answer must stay the same.
Reply with only a JSON list: [{{"id": "...", "en": "...", "fr": "..."}}, ...]

{items}"""


def variants(batch, model):
    items = "\n".join(
        json.dumps({"id": q["id"], "page": q["page"], "question": q["question"]})
        for q in batch
    )
    text = claude_text(
        PROMPT.format(items=items), model, "Reply with JSON only.", timeout=600
    )
    rows = json.loads(re.search(r"\[.*\]", text, re.S).group(0))
    got = {r["id"]: r for r in rows}
    assert set(got) == {q["id"] for q in batch}, "paraphraser skipped questions"
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("questions")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--batch", type=int, default=20)
    args = ap.parse_args()

    data = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    qs = data["questions"]
    batches = [qs[i : i + args.batch] for i in range(0, len(qs), args.batch)]
    with ThreadPoolExecutor(4) as pool:
        got = {}
        for part in pool.map(lambda b: variants(b, args.model), batches):
            got |= part
    out = []
    for q in qs:
        out.append(q | {"base_id": q["id"], "variant": "template"})
        for lang in ("en", "fr"):
            out.append(
                q
                | {
                    "id": f"{q['id']}~{lang}",
                    "base_id": q["id"],
                    "variant": lang,
                    "question": got[q["id"]][lang],
                }
            )
    Path(args.out).write_text(
        json.dumps(data | {"questions": out}, indent=1, ensure_ascii=False)
    )
    print(len(out), "questions")


if __name__ == "__main__":
    main()
