import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

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

/** Advisory identity check: GET ?packager=...&ref_id=... */
export const GET: RequestHandler = async ({ url, fetch }) => {
	const params = new URLSearchParams({
		packager: url.searchParams.get('packager') ?? '',
		ref_id: url.searchParams.get('ref_id') ?? ''
	});
	return forward(
		`${BASE_API_URL}/library-drafts/check-identity/?${params}`,
		'GET',
		undefined,
		fetch
	);
};

/** Create ({action: 'create', ...fields}) or adopt ({action: 'adopt', stored_library}) */
export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body.action;
	delete body.action;
	if (action === 'create') {
		return forward(`${BASE_API_URL}/library-drafts/`, 'POST', body, fetch);
	}
	if (action === 'adopt') {
		return forward(`${BASE_API_URL}/library-drafts/adopt/`, 'POST', body, fetch);
	}
	return json({ error: `unknown action '${action}'` }, { status: 400 });
};

export const DELETE: RequestHandler = async ({ url, fetch }) => {
	const id = url.searchParams.get('id');
	if (!id) {
		return json({ error: 'missing id' }, { status: 400 });
	}
	const r = await fetch(`${BASE_API_URL}/library-drafts/${id}/`, { method: 'DELETE' });
	const text = await r.text();
	return json(text ? JSON.parse(text) : null, { status: r.status });
};
