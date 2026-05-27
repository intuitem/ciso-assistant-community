import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

async function forward(url: string, body: unknown, fetchFn: typeof fetch) {
	const r = await fetchFn(url, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	const text = await r.text();
	const data = text ? JSON.parse(text) : null;
	return json(data, { status: r.status });
}

export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body.action;
	if (action === 'create-blank') {
		return forward(`${BASE_API_URL}/presets/create-blank/`, { name: body.name }, fetch);
	}
	if (action === 'duplicate') {
		return forward(`${BASE_API_URL}/presets/${body.source_id}/duplicate/`, undefined, fetch);
	}
	if (action === 'delete') {
		const r = await fetch(`${BASE_API_URL}/presets/${body.id}/`, { method: 'DELETE' });
		return new Response(null, { status: r.status });
	}
	return json({ error: `unknown action '${action}'` }, { status: 400 });
};
