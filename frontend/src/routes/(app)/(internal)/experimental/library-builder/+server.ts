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
	// Bodyless statuses (204 on DELETE): json() would build a body, which
	// the Response constructor rejects for those statuses.
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

/** Create ({action: 'create', ...fields}) or adopt ({action: 'adopt', stored_library}).
 *  A multipart request (a YAML file upload) is streamed to import-yaml. */
export const POST: RequestHandler = async ({ request, fetch }) => {
	if (request.headers.get('content-type')?.includes('multipart/form-data')) {
		const r = await fetch(`${BASE_API_URL}/library-drafts/import-yaml/`, {
			method: 'POST',
			body: await request.formData()
		});
		const text = await r.text();
		if (!text || r.status === 204) {
			return new Response(null, { status: r.status });
		}
		try {
			return json(JSON.parse(text), { status: r.status });
		} catch {
			return new Response(text, {
				status: r.status,
				headers: { 'Content-Type': r.headers.get('Content-Type') ?? 'text/plain' }
			});
		}
	}
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
	return forward(`${BASE_API_URL}/library-drafts/${id}/`, 'DELETE', undefined, fetch);
};
