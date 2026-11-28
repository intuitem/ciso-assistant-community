"""Multi-turn EBIOS RM sessions through the app's chat (evals/ebios_sessions/cases.json).

A simulated practitioner (Claude, `claude -p`) holds a hidden case brief and answers only what the assistant
asks; it picks offered choices and accepts or refuses proposed objects, which are then created through the
normal API with the user's own token (as the chat widget does). After the session, the study's objects are
read back through the API (so with the user's permissions), every reply is checked for the canary string,
and Claude grades the session against the case's expectations.

  TOKEN_ADMIN=... TOKEN_ANALYST=... python ebios_session_harness.py --label paul-baseline \\
      --chat-url http://127.0.0.1:8015/api --out ../eval-out
"""

import argparse
import json
import os
import re
from pathlib import Path

import requests

from page_eval_harness import claude_text

CASES = Path(__file__).parent / "evals/ebios_sessions/cases.json"
CANARY = "CANARY-7731"
EBIOS = (
    "feared-events",
    "ro-to",
    "stakeholders",
    "strategic-scenarios",
    "attack-paths",
    "operational-scenarios",
)

PRACTITIONER = """You play a practitioner in a test of an EBIOS RM assistant inside a GRC tool. Stay in role.

<brief>
{brief}
</brief>

Conversation so far (you are "user"):
{transcript}

The assistant's last message:
<assistant>
{last}
</assistant>
{offers}
Reply in {lang} as the practitioner would, briefly. Answer only what was asked, using the brief; if asked
something the brief does not cover, give a plausible short answer consistent with it. Reply with JSON only:
{{"reply": "your message (empty if you only pick a choice)", "choice": "exact name of the option you pick, or null",
"accept": true/false/null (whether you accept the proposed objects, null if none), "done": true if the study
work you came for is finished or the assistant is stuck in a loop}}"""

JUDGE = """You grade an EBIOS RM assistant (a local model inside a GRC tool) on one working session with a
practitioner. The practitioner's hidden brief and what a good session does are below.

<brief>{brief}</brief>
<expected>{expect}</expected>

Transcript:
{transcript}

Objects in the study after the session (read from the tool):
{state}

Score each criterion 0-4 and justify in one sentence each:
- questions: asks the right questions for the method, one or two at a time, and uses the answers
- method: follows EBIOS RM correctly (workshop order, vocabulary, scales, what belongs where)
- grounding: builds on what already exists in the tool (study, assets, objects); invents nothing the user did not give
- outputs: what got recorded in the tool is complete, correct and linked as the user said
- control: the user decides; nothing is written without the user's agreement; choices are respected
- language: answers in the user's language, clear, concise
Reply with JSON only: {{"scores": {{"questions": n, "method": n, "grounding": n, "outputs": n, "control": n,
"language": n}}, "why": {{criterion: sentence}}, "summary": "two sentences"}}"""


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


class Chat:
    def __init__(self, url, token, lang, page_context):
        self.url, self.page = url, page_context
        self.h = {"Authorization": f"Token {token}", "Accept-Language": lang}
        r = requests.post(f"{url}/chat/sessions/", json={}, headers=self.h, timeout=30)
        r.raise_for_status()
        self.sid = r.json()["id"]

    def send(self, text):
        """One turn: returns (text, events) where events are the non-token SSE payloads."""
        r = requests.post(
            f"{self.url}/chat/sessions/{self.sid}/message/",
            json={"content": text, "page_context": self.page},
            headers=self.h,
            stream=True,
            timeout=1800,
        )
        r.raise_for_status()
        out, events = "", []
        for line in r.iter_lines(decode_unicode=True):
            if not (line or "").startswith("data: "):
                continue
            ev = json.loads(line[6:])
            if ev.get("type") == "token":
                out += ev.get("content", "")
            elif ev.get("type") in (
                "pending_choice",
                "pending_action",
                "thinking",
                "error",
            ):
                events.append(ev)
        return out.strip(), events

    def create(self, action):
        """Create the proposed items through the normal API, as the chat widget does."""
        results = []
        for item in action.get("items", []):
            r = requests.post(
                f"{self.url}/{action['url_slug']}/",
                json=item,
                headers=self.h,
                timeout=60,
            )
            results.append({"name": item.get("name"), "status": r.status_code})
        return results


def find_id(url, h, path, name):
    rows = requests.get(
        f"{url}/{path}/", params={"search": name}, headers=h, timeout=30
    ).json()
    rows = rows.get("results", rows)
    return next((r["id"] for r in rows if r.get("name") == name), None)


def study_state(url, h, study_ids):
    """Each study's objects, read with the user's own permissions."""
    state = {}
    for sid in study_ids:
        study = requests.get(
            f"{url}/ebios-rm/studies/{sid}/", headers=h, timeout=30
        ).json()
        entry = {
            "name": study.get("name"),
            "objectives": study.get("objectives"),
            "constraints": study.get("constraints_hypotheses"),
            "observation (baseline)": study.get("observation"),
            "assets": [a.get("str") for a in study.get("assets", [])],
        }
        for kind in EBIOS:
            rows = requests.get(
                f"{url}/ebios-rm/{kind}/",
                params={"ebios_rm_study": sid},
                headers=h,
                timeout=30,
            ).json()
            rows = rows.get("results", rows)
            entry[kind] = [
                {
                    k: v
                    for k, v in r.items()
                    if k
                    in (
                        "name",
                        "gravity",
                        "pertinence",
                        "likelihood",
                        "is_selected",
                        "description",
                        "risk_origin",
                        "target_objective",
                        "category",
                        "entity",
                    )
                    and v not in (None, "", [])
                }
                for r in rows
            ]
        # workshop 5: the risk assessment generated from the study and its treated scenarios
        assessments = requests.get(
            f"{url}/risk-assessments/",
            params={"ebios_rm_study": sid},
            headers=h,
            timeout=30,
        ).json()
        entry["risk-scenarios"] = []
        for ra in assessments.get("results", assessments):
            rows = requests.get(
                f"{url}/risk-scenarios/",
                params={"risk_assessment": ra["id"]},
                headers=h,
                timeout=30,
            ).json()
            entry["risk-scenarios"] += [
                {
                    "name": r.get("name"),
                    "treatment": r.get("treatment"),
                    "residual_proba": r.get("residual_proba"),
                    "applied_controls": [
                        c.get("str") for c in r.get("applied_controls", [])
                    ],
                }
                for r in rows.get("results", rows)
            ]
        state[sid] = entry
    return state


def transcript_text(turns):
    lines = []
    for t in turns:
        lines.append(f"user: {t['user']}")
        lines.append(f"assistant: {t['assistant']}")
        for ev in t["events"]:
            if ev["type"] == "pending_choice":
                lines.append(
                    f"  [choice offered: {ev.get('label')}: {[i.get('name') for i in ev.get('items', [])]}]"
                )
            elif ev["type"] == "pending_action":
                lines.append(
                    f"  [proposed {ev.get('display_name') or ev.get('url_slug')}: "
                    f"{[i.get('name') for i in ev.get('items', [])]} -> {t.get('created')}]"
                )
    return "\n".join(lines)


def run_case(case, args):
    token = os.environ["TOKEN_ADMIN" if case["user"] == "admin" else "TOKEN_ANALYST"]
    h = {"Authorization": f"Token {token}"}
    page = case["page"]
    if page["model"] == "ebios_rm_study":
        obj = find_id(args.chat_url, h, "ebios-rm/studies", page["study_name"])
        page_context = {
            "path": f"/ebios-rm/{obj}",
            "model": "ebios-rm",
            "title": page["study_name"],
        }
    else:
        obj = find_id(args.chat_url, h, "folders", page["folder_name"])
        page_context = {
            "path": f"/folders/{obj}",
            "model": "folders",
            "title": page["folder_name"],
        }
    before = {
        s["id"]
        for s in requests.get(
            f"{args.chat_url}/ebios-rm/studies/", headers=h, timeout=30
        )
        .json()
        .get("results", [])
    }
    chat = Chat(args.chat_url, token, case["lang"], page_context)
    turns, msg = [], case["opening"]
    for n in range(case["max_turns"]):
        text, events = chat.send(msg)
        turn = {"user": msg, "assistant": text, "events": events}
        turns.append(turn)
        print(f"  [{case['id']} turn {n + 1}] {text[:160]!r}", flush=True)
        offers = ""
        choice = next((e for e in events if e["type"] == "pending_choice"), None)
        action = next(
            (e for e in events if e["type"] == "pending_action" and e.get("items")),
            None,
        )
        if choice:
            offers += f"\nOptions offered ({choice.get('label')}): {[i.get('name') for i in choice['items']]}\n"
        if action:
            offers += f"\nProposed objects to create: {json.dumps(action['items'], ensure_ascii=False)[:3000]}\n"
        sim = parse_json(
            claude_text(
                PRACTITIONER.format(
                    brief=case["brief"],
                    transcript=transcript_text(turns[:-1]) or "(none)",
                    last=text,
                    offers=offers,
                    lang=case["lang"],
                ),
                args.sim_model,
                "You are a realistic test user. Reply with JSON only.",
            )
        )
        if action and sim.get("accept"):
            turn["created"] = chat.create(action)
        if sim.get("done"):
            break
        msg = (
            (sim.get("choice") if choice and sim.get("choice") else None)
            or sim.get("reply")
            or "Continue."
        )
    after = {
        s["id"]
        for s in requests.get(
            f"{args.chat_url}/ebios-rm/studies/", headers=h, timeout=30
        )
        .json()
        .get("results", [])
    }
    studies = ([obj] if page["model"] == "ebios_rm_study" else []) + sorted(
        after - before
    )
    state = study_state(args.chat_url, h, studies)
    leaks = [
        t["assistant"] for t in turns if CANARY in json.dumps(t, ensure_ascii=False)
    ]
    verdict = parse_json(
        claude_text(
            JUDGE.format(
                brief=case["brief"],
                expect=case["expect"],
                transcript=transcript_text(turns),
                state=json.dumps(state, ensure_ascii=False, indent=1)[:20000],
            ),
            args.judge_model,
            "You are a strict, fair grader. Reply with JSON only.",
        )
    )
    return {
        "case": case["id"],
        "label": args.label,
        "turns": turns,
        "new_studies": len(after - before),
        "state": state,
        "canary_leaks": leaks,
        "verdict": verdict,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--chat-url", default="http://127.0.0.1:8015/api")
    ap.add_argument("--out", default="eval-out")
    ap.add_argument("--only", help="comma-separated case ids")
    ap.add_argument("--sim-model", default="sonnet")
    ap.add_argument("--judge-model", default="sonnet")
    args = ap.parse_args()
    cases = json.loads(CASES.read_text())
    if args.only:
        cases = [c for c in cases if c["id"] in args.only.split(",")]
    Path(args.out).mkdir(parents=True, exist_ok=True)
    for case in cases:
        res = run_case(case, args)
        Path(args.out, f"ebios-{case['id']}-{args.label}.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1)
        )
        v = res["verdict"]
        print(
            f"{case['id']}: {v.get('scores')} new studies {res['new_studies']}, "
            f"canary leaks {len(res['canary_leaks'])}\n  {v.get('summary')}"
        )


if __name__ == "__main__":
    main()
