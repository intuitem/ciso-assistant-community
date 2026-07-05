import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const POST_ACTIONS: Record<string, string> = {
	publish: 'publish',
	'import-objects': 'import-objects',
	'add-framework': 'add-framework',
	'upsert-object': 'upsert-object',
	'delete-object': 'delete-object',
	'preset-editor-preview': 'preset-editor-preview'
};

const GET_ACTIONS: Record<string, string> = {
	read: '',
	validate: 'validate',
	conflicts: 'conflicts'
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

export const GET: RequestHandler = async ({ params, url, fetch }) => {
	const action = url.searchParams.get('action') ?? 'read';
	if (action === 'export') {
		// Stream the YAML through, keeping the attachment headers.
		const r = await fetch(`${BASE_API_URL}/library-drafts/${params.id}/export/`);
		return new Response(await r.blob(), {
			status: r.status,
			headers: {
				'Content-Type': r.headers.get('Content-Type') ?? 'application/yaml',
				'Content-Disposition': r.headers.get('Content-Disposition') ?? 'attachment'
			}
		});
	}
	const path = GET_ACTIONS[action];
	if (path === undefined) {
		return json({ error: `unknown action '${action}'` }, { status: 400 });
	}
	const suffix = path ? `${path}/` : '';
	return forward(`${BASE_API_URL}/library-drafts/${params.id}/${suffix}`, 'GET', undefined, fetch);
};

export const POST: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body.action;
	const path = POST_ACTIONS[action];
	if (!path) {
		return json({ error: `unknown action '${action}'` }, { status: 400 });
	}
	delete body.action;
	return forward(
		`${BASE_API_URL}/library-drafts/${params.id}/${path}/`,
		'POST',
		Object.keys(body).length ? body : undefined,
		fetch
	);
};

export const PATCH: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json();
	return forward(`${BASE_API_URL}/library-drafts/${params.id}/`, 'PATCH', body, fetch);
};
