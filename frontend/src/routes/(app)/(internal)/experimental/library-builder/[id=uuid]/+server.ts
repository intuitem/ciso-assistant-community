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
	// Bodyless statuses (204): json() would build a body, which the
	// Response constructor rejects for those statuses.
	if (!text || r.status === 204) {
		return new Response(null, { status: r.status });
	}
	try {
		return json(JSON.parse(text), { status: r.status });
	} catch {
		// Non-JSON body (e.g. an upstream error page): pass it through with
		// the original status instead of masking it with a parse 500.
		return new Response(text, {
			status: r.status,
			headers: { 'Content-Type': r.headers.get('Content-Type') ?? 'text/plain' }
		});
	}
}

export const GET: RequestHandler = async ({ params, url, fetch }) => {
	// The YAML download lives at the page-less ./export subroute: this route
	// has a +page, so browser navigations get HTML and could never reach an
	// export branch here.
	const action = url.searchParams.get('action') ?? 'read';
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
