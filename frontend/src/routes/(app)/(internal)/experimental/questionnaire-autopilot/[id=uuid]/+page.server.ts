import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

async function fetchJson(fetch: typeof globalThis.fetch, url: string) {
	const res = await fetch(url);
	if (!res.ok) return null;
	return res.json();
}

export const load = (async ({ fetch, params }) => {
	const runRes = await fetch(`${BASE_API_URL}/chat/questionnaire-runs/${params.id}/`);
	if (!runRes.ok) {
		throw error(runRes.status, 'Run not found.');
	}
	const run = await runRes.json();

	const [questionsData, agentRunsData] = await Promise.all([
		fetchJson(
			fetch,
			`${BASE_API_URL}/chat/questionnaire-questions/?questionnaire_run=${params.id}&ordering=ord`
		),
		fetchJson(
			fetch,
			`${BASE_API_URL}/chat/agent-runs/?target_object_id=${params.id}&ordering=-created_at`
		)
	]);

	const questions = questionsData?.results ?? questionsData ?? [];
	const agentRuns = agentRunsData?.results ?? agentRunsData ?? [];
	const latestAgentRun = agentRuns[0] ?? null;

	let actions: any[] = [];
	if (latestAgentRun && latestAgentRun.status === 'succeeded') {
		const actionsData = await fetchJson(
			fetch,
			`${BASE_API_URL}/chat/agent-actions/?agent_run=${latestAgentRun.id}&kind=propose_answer&ordering=-created_at`
		);
		actions = actionsData?.results ?? actionsData ?? [];
	}

	return { run, questions, latestAgentRun, actions };
}) satisfies PageServerLoad;
