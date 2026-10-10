import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const body = await request.json().catch(() => ({}));
	const payload = {
		questionnaire_run: params.id,
		strictness: body.strictness ?? 'fast'
	};
	const res = await fetch(`${BASE_API_URL}/chat/agent-runs/start-questionnaire-prefill/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	const data = await res.json().catch(() => ({}));
	if (!res.ok) {
		console.error('start-prefill failed', { status: res.status, payload, response: data });
	}
	return json(data, { status: res.status });
};
