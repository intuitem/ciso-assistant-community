import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ACTION_PATHS: Record<string, string> = {
	'start-editing': 'start-editing',
	'discard-draft': 'discard-draft',
	'publish-preview': 'publish-draft-preview',
	publish: 'publish-draft'
};

async function forward(url: string, method: string, body: unknown, fetchFn: typeof fetch) {
	const r = await fetchFn(url, {
		method,
		headers: { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	const text = await r.text();
	const data = text ? JSON.parse(text) : null;
	return json(data, { status: r.status });
}

export const POST: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body.action;
	const path = ACTION_PATHS[action];
	if (!path) {
		return json({ error: `unknown action '${action}'` }, { status: 400 });
	}
	delete body.action;
	return forward(
		`${BASE_API_URL}/presets/${params.id}/${path}/`,
		'POST',
		Object.keys(body).length ? body : undefined,
		fetch
	);
};

export const PATCH: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json();
	return forward(`${BASE_API_URL}/presets/${params.id}/save-draft/`, 'PATCH', body, fetch);
};
