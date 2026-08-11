"""Measure tool-selection accuracy against tool-surface size.

Pulls the real MCP tool definitions from ca_mcp, converts them to OpenAI
function specs, and asks a local LM Studio model to answer fixed GRC questions.
Records which tool it picked, so 45-tool (read-only) and 102-tool (full)
surfaces can be compared on identical prompts.

  export LM_API_TOKEN=...
  uv run python tools_selection_harness.py --models qwen/qwen3-4b-2507,qwen/qwen3-8b
"""

import argparse
import asyncio
import json
import os
import sys
import requests

BASE = os.environ.get("LM_BASE", "http://127.0.0.1:1234/v1")
TOKEN = os.environ.get("LM_API_TOKEN", "")

# (prompt, acceptable tool names). Several are deliberately near-miss prone:
# risk scenarios vs quantitative risk scenarios, "domains" vs folders.
PROMPTS = [
    ("List all risk scenarios in the risk registry", {"get_risk_scenarios"}),
    ("What applied controls do we have?", {"get_applied_controls"}),
    ("Show me our assets", {"get_assets"}),
    (
        "Which compliance frameworks are loaded?",
        {"get_frameworks", "get_loaded_libraries"},
    ),
    ("List the domains", {"get_folders"}),
    ("Show me the vulnerabilities", {"get_vulnerabilities"}),
    ("What incidents have been reported?", {"get_incidents"}),
    ("List the third-party entities", {"get_entities"}),
    ("Show the security exceptions", {"get_security_exceptions"}),
    ("What is the progress of our audits?", {"get_audits_progress"}),
    ("List the EBIOS RM studies", {"get_ebios_rm_studies"}),
    ("Show the risk matrices", {"get_risk_matrices"}),
    ("What task templates are defined?", {"get_task_templates"}),
    ("List the business impact analyses", {"get_business_impact_analyses"}),
    ("Show me the stakeholders", {"get_stakeholders"}),
    ("List the perimeters", {"get_perimeters"}),
    ("What threats are in the catalog?", {"get_threats"}),
    ("Show the quantitative risk studies", {"get_quantitative_risk_studies"}),
    # French — memory project_chat_tool_selection_robustness records failures here
    ("Liste les scénarios de risque", {"get_risk_scenarios"}),
    ("Quels sont nos actifs ?", {"get_assets"}),
    ("Montre-moi les vulnérabilités", {"get_vulnerabilities"}),
    ("Liste les entités tierces", {"get_entities"}),
]

# Tier 2. (prompt, acceptable tools, required arg substrings). Harder along four
# axes the easy tier never touched: ambiguity, multi-hop first-step choice,
# parameter extraction, and choosing among WRITE tools rather than avoiding them.
HARD = [
    # -- ambiguous intent: several defensible tools
    (
        "What is our biggest exposure right now?",
        {"get_risk_scenarios", "get_vulnerabilities", "get_incidents"},
        None,
    ),
    (
        "How are we doing on compliance?",
        {
            "get_audits_progress",
            "get_all_audits_with_metrics",
            "get_audit_global_score",
        },
        None,
    ),
    (
        "Where are we most at risk from suppliers?",
        {"get_entity_assessments", "get_entities", "get_solutions"},
        None,
    ),
    # -- multi-hop: only the FIRST step is scored
    (
        "Which controls cover our highest-rated risk scenario?",
        {"get_risk_scenarios", "get_applied_controls"},
        None,
    ),
    (
        "Do we have evidence for the requirements we failed?",
        {"get_requirement_assessments", "get_audit_gap_analysis"},
        None,
    ),
    # -- near-miss traps between genuinely similar tools
    ("Show the quantitative risk scenarios", {"get_quantitative_risk_scenarios"}, None),
    ("Show the quantitative risk studies", {"get_quantitative_risk_studies"}, None),
    (
        "Give me the full details of task template Backup Review",
        {"get_task_template_details"},
        None,
    ),
    ("Show details of risk matrix Critical 5x5", {"get_risk_matrix_details"}, None),
    # -- parameter extraction: right tool AND right argument
    ("List risk scenarios in the Finance domain", {"get_risk_scenarios"}, {"finance"}),
    (
        "Show me the applied controls for the Global domain",
        {"get_applied_controls"},
        {"global"},
    ),
    ("List assets in the Production perimeter", {"get_assets"}, {"production"}),
    (
        "Show requirement assessments for the ISO27001 audit",
        {"get_requirement_assessments"},
        {"iso27001"},
    ),
    # -- write selection (scored only where write tools are present)
    ("Create a new asset called Web Server 01", {"create_asset"}, {"web server 01"}),
    ("Add a threat named Supply chain compromise", {"create_threat"}, {"supply chain"}),
    ("Create a new domain called Legal", {"create_folder"}, {"legal"}),
    # -- French, harder phrasing
    (
        "Quels sont les risques les plus critiques pour nos actifs ?",
        {"get_risk_scenarios", "get_assets"},
        None,
    ),
    ("Crée un actif nommé Serveur Web", {"create_asset"}, {"serveur web"}),
]

# Tier 3. Does the model reach for count_objects on aggregate intent, and does
# it stay away on list intent? The tool's integrity guards are worthless if it
# is never chosen, and harmful if it displaces the list tools.
AGG = [
    # -- positive: the answer is a number, listing would under-report
    ("How many vulnerabilities do we have?", {"count_objects"}, None),
    ("How many risk scenarios are there in total?", {"count_objects"}, None),
    ("Count the incidents", {"count_objects"}, None),
    ("What proportion of applied controls are still to do?", {"count_objects"}, None),
    (
        "Give me a breakdown of risk scenarios by treatment",
        {"count_objects"},
        {"treatment"},
    ),
    (
        "What is the distribution of vulnerabilities by status?",
        {"count_objects"},
        {"status"},
    ),
    ("How many assets are in the Global domain?", {"count_objects"}, {"global"}),
    ("Combien de vulnérabilités avons-nous ?", {"count_objects"}, None),
    # -- negative controls: list intent must NOT be captured by count_objects
    ("Show me our vulnerabilities", {"get_vulnerabilities"}, None),
    ("List the risk scenarios", {"get_risk_scenarios"}, None),
    ("Which applied controls do we have? Show them.", {"get_applied_controls"}, None),
    (
        "Show me the details of risk scenario R.01",
        {"get_risk_scenario", "get_risk_scenarios"},
        None,
    ),
]

# A ~12-tool "core reads" surface: same tool design, fewer of them. Isolates
# tool COUNT from tool QUALITY, which the workstream-A argument depends on.
CORE = {
    "count_objects",
    "get_risk_scenarios",
    "get_applied_controls",
    "get_assets",
    "get_frameworks",
    "get_folders",
    "get_vulnerabilities",
    "get_incidents",
    "get_entities",
    "get_security_exceptions",
    "get_audits_progress",
    "get_threats",
    "get_perimeters",
}

SYSTEM = (
    "You are a GRC assistant with access to the CISO Assistant platform. "
    "Use the provided tools to answer the user's question. Call exactly one tool."
)


CLI_DIR = os.environ.get("CA_CLI_DIR", os.path.dirname(os.path.abspath(__file__)))


def load_tools(read_only: bool):
    """Build a fresh FastMCP per surface — server.register_tools is idempotent."""
    if CLI_DIR not in sys.path:
        sys.path.insert(0, CLI_DIR)
    from mcp.server.fastmcp import FastMCP
    from ca_mcp.server import READ_TOOLS, WRITE_TOOLS

    probe = FastMCP("probe")
    for fn in READ_TOOLS:
        probe.tool()(fn)
    if not read_only:
        for fn in WRITE_TOOLS:
            probe.tool()(fn)
    tools = asyncio.run(probe.list_tools())
    out = []
    for t in tools:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": (t.description or "")[:1024],
                    "parameters": t.inputSchema or {"type": "object", "properties": {}},
                },
            }
        )
    return out


def ask(model, tools, prompt, timeout=180):
    try:
        r = requests.post(
            f"{BASE}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0,
                "max_tokens": 512,
            },
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=timeout,
        )
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:160]}"
        d = r.json()
    except Exception as e:
        return None, f"{type(e).__name__}"
    try:
        msg = d["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
    except (AttributeError, IndexError, KeyError, TypeError):
        return None, "INVALID_RESPONSE"
    if not calls:
        return None, "NO_TOOL_CALL"
    if len(calls) > 1:
        # SYSTEM asks for exactly one call. Scoring calls[0] here would count a
        # scattergun response as correct whenever the first pick happens to match,
        # inflating measured accuracy.
        return None, "MULTIPLE_TOOL_CALLS"
    fn = calls[0]["function"]
    return (fn["name"], fn.get("arguments") or ""), None


def run(model, label, tools, promptset, tier):
    hits = misses = notool = errors = badargs = 0
    detail = []
    present = {t["function"]["name"] for t in tools}
    for entry in promptset:
        prompt, expected, want_args = (
            (entry + (None,))[:3] if len(entry) == 2 else entry
        )
        # Only score prompts this surface can actually answer, so a smaller
        # surface isn't credited for questions it was never offered.
        if not (expected & present):
            continue
        got, err = ask(model, tools, prompt)
        if err == "NO_TOOL_CALL":
            notool += 1
            detail.append((prompt, "(no tool call)", sorted(expected)[0]))
            continue
        if err:
            errors += 1
            detail.append((prompt, f"ERROR {err}", sorted(expected)[0]))
            continue
        name, rawargs = got
        if name not in expected:
            misses += 1
            detail.append((prompt, name, sorted(expected)[0]))
            continue
        if want_args:
            blob = rawargs.lower()
            if not all(w in blob for w in want_args):
                badargs += 1
                detail.append(
                    (prompt, f"{name} args={rawargs[:60]}", f"args~{want_args}")
                )
                continue
        hits += 1
    total = hits + misses + notool + errors + badargs
    payload = len(json.dumps(tools))
    print(
        f"  {tier:<5} {label:<11} {len(tools):>4} tools {payload // 1000:>4}KB | "
        f"correct {hits}/{total} ({100 * hits / max(total, 1):>3.0f}%) | "
        f"wrong-tool {misses} | bad-args {badargs} | no-call {notool} | err {errors}",
        flush=True,
    )
    return detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--models", required=True, help="comma-separated LM Studio model ids"
    )
    ap.add_argument("--tier", default="both", choices=["easy", "hard", "agg", "both"])
    args = ap.parse_args()

    if not TOKEN:
        sys.exit("LM_API_TOKEN not set")

    ro = load_tools(True)
    surfaces = [
        ("core", [t for t in ro if t["function"]["name"] in CORE]),
        ("read-only", ro),
        ("full", load_tools(False)),
    ]

    tiers = [("easy", PROMPTS), ("hard", HARD), ("agg", AGG)]
    if args.tier != "both":
        tiers = [t for t in tiers if t[0] == args.tier]

    all_detail = {}
    for model in args.models.split(","):
        model = model.strip()
        print(f"\n{model}", flush=True)
        for tier, pset in tiers:
            for label, tools in surfaces:
                all_detail[(model, f"{tier}/{label}")] = run(
                    model, label, tools, pset, tier
                )

    print("\n\nMistakes (prompt -> picked / expected)")
    for (model, label), detail in all_detail.items():
        if not detail:
            continue
        print(f"\n{model} | {label}")
        for prompt, picked, expected in detail:
            print(f"  {prompt[:44]:<46} {picked:<34} want {expected}")


if __name__ == "__main__":
    main()
