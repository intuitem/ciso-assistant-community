import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, url }) => {
	const runId = url.searchParams.get('run_id');
	if (!runId) {
		return json({ detail: 'run_id required' }, { status: 400 });
	}
	const res = await fetch(`${BASE_API_URL}/chat/agent-runs/${runId}/cancel/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: '{}'
	});
	const data = await res.json().catch(() => ({}));
	return json(data, { status: res.status });
};
