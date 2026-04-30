import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const runId = url.searchParams.get('run_id');
	if (!runId) {
		return json({ detail: 'run_id required' }, { status: 400 });
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
	const actionsData = await actionsRes.json().catch(() => ({}));
	const actions = actionsData?.results ?? actionsData ?? [];

	// Filter to currently active proposals (drop expired iterations)
	const activeActions = actions.filter((a: any) => a.state !== 'expired');

	return json({ agentRun, actions: activeActions });
};
