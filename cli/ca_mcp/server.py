"""Main MCP server entry point for CISO Assistant"""

import asyncio
import contextvars
import functools
import logging
import time
from urllib.parse import urlsplit

import anyio.to_thread
from mcp.server.mcpserver import MCPServer

from . import actions, config
from .auth import capture_headers
from .utils.response_formatter import _cap

logger = logging.getLogger(__name__)

mcp = MCPServer("ciso-assistant", middleware=[capture_headers])

# Import all tools to register them with the MCP server
from .tools.read_tools import (
    get_risk_scenarios,
    get_risk_scenario,
    get_applied_controls,
    get_audits_progress,
    get_folders,
    get_perimeters,
    get_risk_matrices,
    get_risk_matrix_details,
    get_risk_assessments,
    get_threats,
    get_assets,
    get_asset_security_gaps,
    get_incidents,
    get_security_exceptions,
    get_frameworks,
    get_business_impact_analyses,
    get_requirement_assessments,
    get_quantitative_risk_studies,
    get_quantitative_risk_scenarios,
    get_quantitative_risk_hypotheses,
    get_task_templates,
    get_task_template_details,
    get_vulnerabilities,
    get_vulnerability,
    get_asset_classes,
    get_users,
    get_teams,
)

from .tools.aggregate_tools import count_objects
from .tools.generic_tools import list_objects, get_object

from .tools.analysis_tools import (
    get_all_audits_with_metrics,
    get_audit_gap_analysis,
    get_audit_global_score,
)

from .tools.library_tools import (
    get_stored_libraries,
    get_loaded_libraries,
    import_stored_library,
    find_requirements,
    get_requirement_mappings,
)

from .tools.write_tools import (
    create_folder,
    create_team,
    create_perimeter,
    create_asset,
    create_threat,
    create_applied_control,
    create_risk_assessment,
    sync_risk_assessment_from_ebios_rm,
    create_risk_scenario,
    create_business_impact_analysis,
    create_compliance_assessment,
    create_quantitative_risk_study,
    create_quantitative_risk_scenario,
    create_quantitative_risk_hypothesis,
    refresh_quantitative_risk_study_simulations,
    create_task_template,
    create_vulnerability,
    create_findings_assessment,
    create_finding,
    create_evidence,
    create_incident,
    create_timeline_entry,
)

from .tools.update_tools import (
    update_team,
    update_folder,
    update_user,
    update_evidence,
    update_asset,
    update_risk_scenario,
    update_applied_control,
    update_risk_assessment,
    update_perimeter,
    update_requirement_assessment,
    update_requirement_assessments,
    update_quantitative_risk_study,
    update_quantitative_risk_scenario,
    update_quantitative_risk_hypothesis,
    update_task_template,
    delete_task_template,
    update_vulnerability,
    delete_vulnerability,
    update_finding,
    update_incident,
    update_timeline_entry,
)

from .tools.evidence_review_tools import (
    get_evidences_to_review,
    read_evidence,
    review_evidence,
)
from .tools.tprm_tools import (
    # Read tools
    get_entities,
    get_entity_assessments,
    get_representatives,
    get_solutions,
    get_contracts,
    # Write tools
    create_entity,
    create_entity_assessment,
    create_representative,
    create_solution,
    create_contract,
    # Update tools
    update_entity,
    update_entity_assessment,
    update_representative,
    update_solution,
    update_contract,
)

from .tools.ebios_rm_tools import (
    # Read tools
    get_ebios_rm_studies,
    get_feared_events,
    get_ro_to_couples,
    get_stakeholders,
    get_strategic_scenarios,
    get_attack_paths,
    get_operational_scenarios,
    get_elementary_actions,
    get_operating_modes,
    get_kill_chains,
    get_operating_mode_quotation,
    # Write tools
    create_ebios_rm_study,
    create_feared_event,
    create_ro_to_couple,
    create_stakeholder,
    create_strategic_scenario,
    create_attack_path,
    create_operational_scenario,
    create_elementary_action,
    create_operating_mode,
    create_kill_chain_step,
    # Update tools
    update_ebios_rm_study,
    update_feared_event,
    update_ro_to_couple,
    update_stakeholder,
    update_strategic_scenario,
    update_attack_path,
    update_operational_scenario,
    update_operating_mode,
    update_kill_chain_step,
)

READ_TOOLS = [
    get_evidences_to_review,
    read_evidence,
    find_requirements,
    get_requirement_mappings,
    count_objects,
    list_objects,
    get_object,
    get_risk_scenarios,
    get_risk_scenario,
    get_applied_controls,
    get_audits_progress,
    get_folders,
    get_perimeters,
    get_risk_matrices,
    get_risk_matrix_details,
    get_risk_assessments,
    get_threats,
    get_assets,
    get_asset_security_gaps,
    get_incidents,
    get_security_exceptions,
    get_frameworks,
    get_business_impact_analyses,
    get_requirement_assessments,
    get_quantitative_risk_studies,
    get_quantitative_risk_scenarios,
    get_quantitative_risk_hypotheses,
    get_task_templates,
    get_task_template_details,
    get_vulnerabilities,
    get_vulnerability,
    get_asset_classes,
    get_users,
    get_teams,
    get_all_audits_with_metrics,
    get_audit_gap_analysis,
    get_audit_global_score,
    get_stored_libraries,
    get_loaded_libraries,
    get_entities,
    get_entity_assessments,
    get_representatives,
    get_solutions,
    get_contracts,
    get_ebios_rm_studies,
    get_feared_events,
    get_ro_to_couples,
    get_stakeholders,
    get_strategic_scenarios,
    get_attack_paths,
    get_operational_scenarios,
    get_elementary_actions,
    get_operating_modes,
    get_kill_chains,
    get_operating_mode_quotation,
]

# Each write tool's action is declared here, not guessed from its name: a tool
# missing from both lists fails tests/mcp/test_actions.py.
CREATE_TOOLS = [
    import_stored_library,
    create_folder,
    create_team,
    create_perimeter,
    create_asset,
    create_threat,
    create_applied_control,
    create_risk_assessment,
    create_risk_scenario,
    create_business_impact_analysis,
    create_compliance_assessment,
    create_quantitative_risk_study,
    create_quantitative_risk_scenario,
    create_quantitative_risk_hypothesis,
    create_task_template,
    create_vulnerability,
    create_findings_assessment,
    create_finding,
    create_evidence,
    create_incident,
    create_timeline_entry,
    create_entity,
    create_entity_assessment,
    create_representative,
    create_solution,
    create_contract,
    create_ebios_rm_study,
    create_feared_event,
    create_ro_to_couple,
    create_stakeholder,
    create_strategic_scenario,
    create_attack_path,
    create_operational_scenario,
    create_elementary_action,
    create_operating_mode,
    create_kill_chain_step,
]

UPDATE_TOOLS = [
    update_folder,
    update_team,
    update_user,
    sync_risk_assessment_from_ebios_rm,
    refresh_quantitative_risk_study_simulations,
    update_vulnerability,
    update_finding,
    update_evidence,
    review_evidence,
    update_incident,
    update_timeline_entry,
    update_asset,
    update_risk_scenario,
    update_applied_control,
    update_risk_assessment,
    update_perimeter,
    update_requirement_assessment,
    update_requirement_assessments,
    update_quantitative_risk_study,
    update_quantitative_risk_scenario,
    update_quantitative_risk_hypothesis,
    update_task_template,
    update_entity,
    update_entity_assessment,
    update_representative,
    update_solution,
    update_contract,
    update_ebios_rm_study,
    update_feared_event,
    update_ro_to_couple,
    update_stakeholder,
    update_strategic_scenario,
    update_attack_path,
    update_operational_scenario,
    update_operating_mode,
    update_kill_chain_step,
]

DELETE_TOOLS = [delete_task_template, delete_vulnerability]

WRITE_TOOLS = CREATE_TOOLS + UPDATE_TOOLS + DELETE_TOOLS

TOOL_ACTIONS = {
    **{tool.__name__: actions.READ for tool in READ_TOOLS},
    **{tool.__name__: actions.CREATE for tool in CREATE_TOOLS},
    **{tool.__name__: actions.UPDATE for tool in UPDATE_TOOLS},
    **{tool.__name__: actions.DELETE for tool in DELETE_TOOLS},
}

# Tools that do more than their action says.
ALSO_NEEDS = {
    # creates the risk scenarios that are missing
    sync_risk_assessment_from_ebios_rm.__name__: {actions.CREATE},
    # the backend checks add_ on this action, though it updates the study
    refresh_quantitative_risk_study_simulations.__name__: {actions.CREATE},
    # same: the decision is a POST on the version
    review_evidence.__name__: {actions.CREATE},
}


def needed_actions(name: str) -> set[str]:
    return {TOOL_ACTIONS.get(name, actions.READ)} | ALSO_NEEDS.get(name, set())


LOOPBACK_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
LOOPBACK_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]

_registered = False

READ_SCOPE = "mcp"


def _annotations(fn, is_read):
    """Behaviour hints so a client can gate destructive calls. Annotations are
    hints, not a security boundary — the read-only profile is the boundary.

    Read/write comes from which list the tool is in, not from its name: a name
    prefix silently mislabels anything that isn't called get_*.
    """
    from mcp.types import ToolAnnotations

    if is_read:
        return ToolAnnotations(
            read_only_hint=True, destructive_hint=False, idempotent_hint=True
        )
    name = fn.__name__
    if name.startswith("delete_"):
        return ToolAnnotations(
            read_only_hint=False, destructive_hint=True, idempotent_hint=True
        )
    # review_: overwrites an earlier decision and the evidence status
    if name.startswith(("update_", "sync_", "review_")):
        return ToolAnnotations(
            read_only_hint=False, destructive_hint=True, idempotent_hint=True
        )
    # create_/import_/refresh_: additive, and not idempotent
    return ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=False
    )


def _offload(fn):
    """Run a tool in a worker thread: tools are `async def` but do blocking I/O,
    which under HTTP stalls every other caller. Converting them to `def` would not
    help -- MCPServer calls sync tools inline on the loop too.
    """

    @functools.wraps(fn)
    async def runner(*args, **kwargs):
        context = contextvars.copy_context()
        result = await anyio.to_thread.run_sync(
            lambda: context.run(asyncio.run, fn(*args, **kwargs))
        )
        # backstop: tools returning a raw string bypass success_response's cap
        return _cap(result) if isinstance(result, str) else result

    return runner


# Change users or domains: an injected agent could change an email and take
# the account over through a password reset. Only a local user with a PAT gets them.
ADMIN_TOOLS = (create_folder, update_folder, update_user)


def _register_on(server, read_only, guard_write=None, hooks=None, remote=False):
    def add(tool, runner, is_read):
        if hooks:
            runner = _with_hooks(runner, tool.__name__, hooks)
        server.tool(annotations=_annotations(tool, is_read=is_read))(runner)

    for tool in READ_TOOLS:
        add(tool, _offload(tool), is_read=True)
    if read_only:
        return
    for tool in WRITE_TOOLS:
        # reads files from the server's disk: only for a local stdio user
        if (remote or config.IS_HTTP) and tool is create_evidence:
            continue
        if remote and tool in ADMIN_TOOLS:
            continue
        runner = _offload(tool)
        if guard_write:
            runner = guard_write(runner, needed_actions(tool.__name__))
        add(tool, runner, is_read=False)


def _with_hooks(runner, name, hooks):
    """Let the host refuse a call before it runs (limits) and record it after
    (logging). Outermost, so refusals by the action guard are recorded too. The
    hooks may block (database, cache): they run in a thread."""
    from mcp.server.auth.middleware.auth_context import get_access_token

    @functools.wraps(runner)
    async def hooked(*args, **kwargs):
        access = get_access_token()
        refusal = await anyio.to_thread.run_sync(hooks.before, name, access)
        if refusal:
            await anyio.to_thread.run_sync(
                lambda: hooks.after(name, access, refusal, 0.0, "limited")
            )
            return refusal
        start = time.monotonic()
        try:
            result = await runner(*args, **kwargs)
        except BaseException as e:
            failure = type(e).__name__ if isinstance(e, Exception) else "cancelled"
            elapsed = time.monotonic() - start
            # a cancelled call is recorded too: shield the hook from the cancel
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(
                    lambda: hooks.after(name, access, None, elapsed, failure)
                )
            raise
        await anyio.to_thread.run_sync(
            lambda: hooks.after(name, access, result, time.monotonic() - start, None)
        )
        return result

    return hooked


def register_tools(read_only: bool = False):
    """Register tools with the MCP server, optionally omitting writes."""
    global _registered
    if _registered:
        return
    _register_on(mcp, read_only)
    _registered = True


def _log_startup(surface):
    logger.info(
        "%s | API_URL=%s read_only=%s tools=%d",
        surface,
        config.API_URL or "<unset>",
        config.READ_ONLY,
        len(READ_TOOLS) if config.READ_ONLY else len(READ_TOOLS) + len(WRITE_TOOLS),
    )


def run_server():
    """Run the MCP server over stdio"""
    register_tools(read_only=config.READ_ONLY)
    _log_startup("MCP stdio")
    mcp.run(transport="stdio")


def _transport_security():
    from mcp.server.transport_security import TransportSecuritySettings

    if config.ALLOWED_HOSTS == ["*"]:
        security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
        logger.warning(
            "CA_MCP_ALLOWED_HOSTS='*': DNS rebinding protection DISABLED. "
            "Acceptable for tunnel testing, never for a real deployment."
        )
    elif config.ALLOWED_HOSTS:
        # Keep loopback allowed so local tooling (Inspector, curl) still reaches
        # the server once a public hostname is configured.
        # https only: trusting http://<public-host> as an Origin would weaken the
        # rebinding check for no benefit. Loopback plaintext is in LOOPBACK_ORIGINS.
        origins = config.ALLOWED_ORIGINS or [
            f"https://{host}" for host in config.ALLOWED_HOSTS
        ]
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=config.ALLOWED_HOSTS + LOOPBACK_HOSTS,
            allowed_origins=origins + LOOPBACK_ORIGINS,
        )
        logger.info("Allowed hosts: %s", config.ALLOWED_HOSTS + LOOPBACK_HOSTS)
    else:
        # explicit: the SDK only defaults to this when bound to a loopback host
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=LOOPBACK_HOSTS,
            allowed_origins=LOOPBACK_ORIGINS,
        )
        logger.warning(
            "CA_MCP_ALLOWED_HOSTS unset: only loopback hosts are accepted. "
            "Set it to the public hostname before exposing this server."
        )
    return security


def build_http_app():
    register_tools(read_only=config.READ_ONLY)
    security = _transport_security()

    _log_startup(
        f"MCP Streamable HTTP on {config.HTTP_HOST}:{config.HTTP_PORT}{config.HTTP_PATH}"
    )
    logger.info(
        "stateless=%s json_response=%s allow_env_token=%s",
        config.STATELESS,
        config.JSON_RESPONSE,
        config.ALLOW_ENV_TOKEN,
    )
    return mcp.streamable_http_app(
        streamable_http_path=config.HTTP_PATH,
        json_response=config.JSON_RESPONSE,
        stateless_http=config.STATELESS,
        transport_security=security,
        host=config.HTTP_HOST,
    )


def _require_action(runner, needed):
    from mcp.server.auth.middleware.auth_context import get_access_token

    @functools.wraps(runner)
    async def guarded(*args, **kwargs):
        access = get_access_token()
        missing = needed - actions.granted_actions(access)
        if missing:
            first = min(missing, key=actions.ACTIONS.index)
            return actions.refusal(access, first)
        return await runner(*args, **kwargs)

    return guarded


class ActionFilteredServer(MCPServer):
    """Lists only the tools the connection's actions allow, so the agent does not
    try the others. The guard on each tool is the boundary; this is for the agent."""

    async def list_tools(self):
        from mcp.server.auth.middleware.auth_context import get_access_token

        granted = actions.granted_actions(get_access_token())
        return [
            tool
            for tool in await super().list_tools()
            if needed_actions(tool.name) <= granted
        ]


async def get_my_access() -> str:
    """What this connection may do in CISO Assistant (read, create, change and
    delete), and which profile it uses. Call it before planning changes."""
    from mcp.server.auth.middleware.auth_context import get_access_token

    return actions.summary(get_access_token())


def build_oauth_http_app(token_verifier, issuer_url, resource_url, hooks=None):
    """Streamable HTTP app for a host that authenticates callers with OAuth.

    `hooks`, if given, has `before(tool, access) -> refusal or None` and
    `after(tool, access, result, seconds, error)`, called around every tool."""
    from mcp.server.auth.settings import AuthSettings
    from starlette.responses import JSONResponse

    # what a connection may do comes from the backend, which enforces it too;
    # CA_MCP_READ_ONLY narrows every connection to the read tools
    read_only = config.READ_ONLY
    server = ActionFilteredServer(
        "ciso-assistant",
        instructions="Call get_my_access to see what this connection may do.",
        token_verifier=token_verifier,
        auth=AuthSettings(
            issuer_url=issuer_url,
            resource_server_url=resource_url,
            required_scopes=[READ_SCOPE],
            validate_token_resource=True,
        ),
    )
    _register_on(
        server, read_only, guard_write=_require_action, hooks=hooks, remote=True
    )
    runner = (
        _with_hooks(get_my_access, "get_my_access", hooks) if hooks else get_my_access
    )
    server.tool(annotations=_annotations(get_my_access, is_read=True))(runner)
    _log_startup(
        f"MCP Streamable HTTP (OAuth) on {config.HTTP_HOST}:{config.HTTP_PORT}{config.HTTP_PATH}"
    )
    app = server.streamable_http_app(
        streamable_http_path=config.HTTP_PATH,
        json_response=config.JSON_RESPONSE,
        stateless_http=config.STATELESS,
        transport_security=_transport_security(),
        host=config.HTTP_HOST,
    )

    metadata_path = (
        "/.well-known/oauth-protected-resource" + urlsplit(resource_url).path
    )
    metadata = {
        "resource": resource_url,
        "authorization_servers": [issuer_url],
        "scopes_supported": [READ_SCOPE],
        "bearer_methods_supported": ["header"],
    }

    async def with_metadata(scope, receive, send):
        if scope["type"] == "http" and scope["path"] == metadata_path:
            response = JSONResponse(
                metadata, headers={"Access-Control-Allow-Origin": "*"}
            )
            await response(scope, receive, send)
            return
        await app(scope, receive, send)

    return isolated(with_metadata)


# set by this server only, whatever the upstream sent
_REPLACED_HEADERS = {
    b"set-cookie",
    b"service-worker-allowed",
    b"content-security-policy",
    b"x-content-type-options",
}


def isolated(app):
    """The proxy rules of /mcp, applied here too, against this server's own
    mistakes: its responses cannot act as a page or a service worker of the
    instance's origin, and the session cookie, which still reaches this process
    when the ingress does not strip it, is dropped before any of its code sees
    it. A compromised server can undo all of this; only the proxy cannot be."""

    async def wrapped(scope, receive, send):
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        headers = [(k, v) for k, v in scope["headers"] if k.lower() != b"cookie"]

        async def send_isolated(message):
            if message["type"] == "http.response.start":
                kept = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() not in _REPLACED_HEADERS
                ]
                kept += [
                    (b"content-security-policy", b"sandbox"),
                    (b"x-content-type-options", b"nosniff"),
                ]
                message = {**message, "headers": kept}
            await send(message)

        await app({**scope, "headers": headers}, receive, send_isolated)

    return wrapped


def run_http():
    """Run the MCP server over Streamable HTTP"""
    import uvicorn

    if config.AUTH_MODE == "oauth":
        from .remote import build_app

        app = build_app()
    else:
        app = build_http_app()
    uvicorn.run(app, host=config.HTTP_HOST, port=config.HTTP_PORT)


def main():
    logging.basicConfig(level=logging.INFO)
    if config.AUTH_MODE not in ("pat", "oauth"):
        raise SystemExit(f"CA_MCP_AUTH must be pat or oauth, not {config.AUTH_MODE!r}")
    if config.AUTH_MODE == "oauth" and not config.IS_HTTP:
        raise SystemExit("CA_MCP_AUTH=oauth needs CA_MCP_TRANSPORT=streamable-http")
    if config.IS_HTTP:
        run_http()
    else:
        run_server()


if __name__ == "__main__":
    main()
