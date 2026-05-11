import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// run_id comes from the client and is interpolated straight into a backend
// URL path. Reject anything that isn't a UUID before issuing the fetches —
// stops a value like "../agent-actions" from path-traversing to a different
// endpoint under the caller's session credentials.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const runId = url.searchParams.get('run_id');
	if (!runId) {
		return json({ detail: 'run_id required' }, { status: 400 });
	}
	if (!UUID_RE.test(runId)) {
		return json({ detail: 'invalid run_id' }, { status: 400 });
	}

	const [runRes, actionsRes] = await Promise.all([
		fetch(`${BASE_API_URL}/chat/agent-runs/${runId}/`),
		fetch(
			`${BASE_API_URL}/chat/agent-actions/?agent_run=${runId}&kind=propose_answer&ordering=-created_at`
		)
	]);

	if (!runRes.ok) {
		return json({ detail: 'agent run not found' }, { status: runRes.status });
	}
	const agentRun = await runRes.json();

	// The actions request is best-effort: a non-OK response, an unparseable
	// body, or a non-paginated JSON error like {"detail": "..."} should all
	// degrade to "no actions yet" rather than 500-ing the whole polling
	// endpoint. Normalize to an array before .filter().
	let actions: unknown[] = [];
	if (actionsRes.ok) {
		const actionsData = await actionsRes.json().catch(() => null);
		const candidate =
			actionsData && typeof actionsData === 'object' && 'results' in actionsData
				? (actionsData as { results: unknown }).results
				: actionsData;
		if (Array.isArray(candidate)) {
			actions = candidate;
		}
	}

	// Filter to currently active proposals (drop expired iterations)
	const activeActions = actions.filter((a: any) => a?.state !== 'expired');

	return json({ agentRun, actions: activeActions });
};
