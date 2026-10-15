"""Measure topic retrieval ("which parts of X deal with MFA?") against evals/topic_gold.

Retrieval stages, all over one framework's assessable requirements:
  lexical   IDF-weighted query-word overlap on name + description
  semantic  cosine on the chat indexer's text (_build_library_entry_text), product embedder
  hybrid    reciprocal-rank fusion of the two
  rerank    cross-encoder over the hybrid top-N
Then optionally an LLM filter (LM Studio) keeps the relevant candidates (--filter-models).

Usage:
  python topic_eval.py                                   # retrieval metrics only
  python topic_eval.py --filter-models qwen/qwen3.5-9b   # + end-to-end filter
"""

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
GOLD = HERE / "evals/topic_gold"
EMBEDDER = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RERANKER = "BAAI/bge-reranker-v2-m3"
STOP = set(
    "a an and or of the to in for on with by is are be as at from that this".split()
)


def words(s):
    return [w for w in re.findall(r"\w+", (s or "").lower()) if w not in STOP]


def entry_text(fw_name, r):
    # mirrors chat.tasks._build_library_entry_text
    parts = [f"Framework: {fw_name}"]
    if r.get("ref_id"):
        parts.append(f"Reference: {r['ref_id']}")
    if r.get("name"):
        parts.append(f"Name: {r['name']}")
    if r.get("description"):
        parts.append(f"Description: {r['description']}")
    return "\n".join(parts)


def lexical_rank(query, rows):
    docs = [set(words(f"{r.get('name')} {r.get('description')}")) for r in rows]
    n = len(docs)
    idf = {
        w: math.log(1 + n / (1 + sum(w in d for d in docs))) for w in set(words(query))
    }
    scores = [sum(v for w, v in idf.items() if w in d) for d in docs]
    order = sorted(range(n), key=lambda i: -scores[i])
    return [i for i in order if scores[i] > 0]


def rrf(*rankings, k=60):
    s = {}
    for ranking in rankings:
        for pos, i in enumerate(ranking):
            s[i] = s.get(i, 0) + 1 / (k + pos + 1)
    return sorted(s, key=lambda i: -s[i])


def recall_at(ranking, gold, k):
    return len(set(ranking[:k]) & gold) / len(gold) if gold else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


FILTER_PROMPT = """You are given numbered requirements from {fw}. Which of them deal with {topic}?
Include requirements that are mainly about it and those where it materially contributes; exclude loose connections.
Reply with only the numbers, comma-separated, or "none".

{items}"""


class OllamaEmbedder:
    """Same encode() shape as SentenceTransformer, over Ollama's /api/embed."""

    def __init__(self, model):
        self.model = model

    def encode(self, texts, normalize_embeddings=True):
        import requests

        out = []
        for i in range(0, len(texts), 64):
            res = requests.post(
                "http://127.0.0.1:11434/api/embed",
                json={"model": self.model, "input": texts[i : i + 64]},
                timeout=600,
            )
            res.raise_for_status()
            out += res.json()["embeddings"]
        v = np.array(out, dtype=np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)


def llm_filter(model, fw, topic, rows):
    import requests

    from multiturn_harness import BASE, TOKEN

    items = "\n".join(
        f"{n}. [{r.get('ref_id')}] {r.get('name') or ''} {(r.get('description') or '')[:400]}"
        for n, r in enumerate(rows, 1)
    )
    res = requests.post(
        f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": FILTER_PROMPT.format(fw=fw, topic=topic, items=items),
                }
            ],
            "temperature": 0,
            "max_tokens": 1024,
            "reasoning_effort": "none",
        },
        timeout=600,
    )
    res.raise_for_status()
    text = res.json()["choices"][0]["message"].get("content") or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    picked = {int(x) for x in re.findall(r"\d+", text)}
    return [i for i in range(len(rows)) if i + 1 in picked]


def selfcheck():
    rows = [
        {"name": "Backup policy"},
        {"name": "MFA for remote access"},
        {"name": "Logs"},
    ]
    assert lexical_rank("multi-factor MFA", rows) == [1]
    assert rrf([0, 1], [1, 2]) == [1, 0, 2]
    assert recall_at([3, 1, 2], {1, 9}, 2) == 0.5


def main():
    selfcheck()
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--frameworks", help="comma-separated gold file stems (default: all)"
    )
    ap.add_argument("--rerank-top", type=int, default=50)
    ap.add_argument("--no-rerank", action="store_true")
    ap.add_argument("--filter-models", help="comma-separated LM Studio models")
    ap.add_argument(
        "--filter-k", type=int, default=30, help="candidates shown to the LLM"
    )
    ap.add_argument(
        "--filter-stage",
        default="rerank",
        choices=["lexical", "semantic", "hybrid", "rerank"],
    )
    ap.add_argument(
        "--filter-batch", type=int, help="split candidates into LLM calls of this size"
    )
    ap.add_argument(
        "--embedder",
        default=EMBEDDER,
        help="sentence-transformers id or ollama:<model>",
    )
    ap.add_argument(
        "--query-prefix", default="", help='e.g. "query: " for arctic-embed'
    )
    ap.add_argument("--results", help="per topic×framework JSONL")
    args = ap.parse_args()

    from sentence_transformers import SentenceTransformer

    topics = {
        k: v
        for k, v in json.loads((GOLD / "topics.json").read_text()).items()
        if not k.startswith("_")
    }
    stems = (
        args.frameworks.split(",")
        if args.frameworks
        else sorted(p.stem for p in GOLD.glob("*.json") if p.stem != "topics")
    )
    emb = (
        OllamaEmbedder(args.embedder.split(":", 1)[1])
        if args.embedder.startswith("ollama:")
        else SentenceTransformer(args.embedder)
    )
    reranker = None
    if not args.no_rerank:
        from sentence_transformers import CrossEncoder

        reranker = CrossEncoder(RERANKER)

    stages = ["lexical", "semantic", "hybrid"] + ([] if args.no_rerank else ["rerank"])
    ks = (10, 25, 50, 100)
    agg = {}  # (stage, grade, k) -> [recall]
    filt = {}  # model -> [(precision, recall_core, recall_all)]
    out = open(args.results, "w") if args.results else None
    for stem in stems:
        gold = json.loads((GOLD / f"{stem}.json").read_text())["labels"]
        rows = [
            json.loads(l)
            for l in (GOLD / "src" / f"{stem}.jsonl").read_text().split("\n")[:-1]
        ]
        idx = {r["urn"]: i for i, r in enumerate(rows)}
        assert set(gold) <= set(idx), f"{stem}: gold urns missing from source"
        vecs = emb.encode(
            [entry_text(stem, r) for r in rows], normalize_embeddings=True
        )
        for topic, spec in topics.items():
            core = {idx[u] for u, t in gold.items() if t.get(topic) == "core"}
            alls = {idx[u] for u, t in gold.items() if topic in t}
            if not alls:
                continue
            q = spec["query"]
            ranks = {"lexical": lexical_rank(q, rows)}
            qv = emb.encode([args.query_prefix + q], normalize_embeddings=True)[0]
            ranks["semantic"] = list(np.argsort(-(vecs @ qv)))
            ranks["hybrid"] = rrf(ranks["lexical"], ranks["semantic"])
            if reranker:
                top = ranks["hybrid"][: args.rerank_top]
                s = reranker.predict([(q, entry_text(stem, rows[i])) for i in top])
                ranks["rerank"] = [top[j] for j in np.argsort(-s)]
            rec = {
                "framework": stem,
                "topic": topic,
                "n_core": len(core),
                "n_all": len(alls),
            }
            for st in stages:
                for k in ks:
                    for grade, g in (("core", core), ("all", alls)):
                        r = recall_at(ranks[st], g, k)
                        agg.setdefault((st, grade, k), []).append(r)
                        rec[f"{st}_{grade}@{k}"] = r
            for model in (args.filter_models or "").split(","):
                if not model:
                    continue
                cand = ranks[args.filter_stage][: args.filter_k]
                b = args.filter_batch or len(cand)
                kept = {
                    batch[j]
                    for batch in (cand[o : o + b] for o in range(0, len(cand), b))
                    for j in llm_filter(
                        model, stem, spec["query"], [rows[i] for i in batch]
                    )
                }
                p = len(kept & alls) / len(kept) if kept else 0.0
                filt.setdefault(model, []).append(
                    (
                        p,
                        recall_at(list(kept), core, len(kept)),
                        recall_at(list(kept), alls, len(kept)),
                    )
                )
                rec[f"filter:{model}"] = {
                    "precision": p,
                    "kept": [rows[i]["ref_id"] for i in kept],
                    "missed_core": [rows[i]["ref_id"] for i in core - kept],
                }
            if out:
                out.write(json.dumps(rec) + "\n")
            print(
                f"{stem:<24} {topic:<18} core {len(core):>3} all {len(alls):>3}  "
                + "  ".join(f"{st[:4]}@25 {rec[f'{st}_all@25']:.2f}" for st in stages),
                flush=True,
            )
    print("\nmean recall (topic × framework):")
    print(f"{'stage':<10}{'grade':<6}" + "".join(f"@{k:<7}" for k in ks))
    for st in stages:
        for grade in ("core", "all"):
            print(
                f"{st:<10}{grade:<6}"
                + "".join(f"{mean(agg[(st, grade, k)]):<8.2f}" for k in ks)
            )
    for model, xs in filt.items():
        print(
            f"\nLLM filter {model} on {args.filter_stage}@{args.filter_k}: "
            f"precision {mean([x[0] for x in xs]):.2f}  recall core {mean([x[1] for x in xs]):.2f}  "
            f"recall all {mean([x[2] for x in xs]):.2f}"
        )
    if out:
        out.close()


if __name__ == "__main__":
    main()
