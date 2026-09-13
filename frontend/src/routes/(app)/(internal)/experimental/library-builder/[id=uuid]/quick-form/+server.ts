import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * Adapter speaking the FrameworkBuilder `_action` protocol against the quick
 * form object stored inside a LibraryDraft document. Same contract as the
 * framework adapter next door; the reference catalog does not apply (pages
 * carry no threat or control links) and answers 400 so the editor hides it.
 */

async function backend(url: string, method: string, body: unknown, fetchFn: typeof fetch) {
	const r = await fetchFn(url, {
		method,
		headers: { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
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

export const POST: RequestHandler = async ({ params, request, url, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body._action;
	const quickFormUrn = url.searchParams.get('quick_form_urn') ?? undefined;
	const base = `${BASE_API_URL}/library-drafts/${params.id}`;

	if (action === 'start-editing') {
		const query = quickFormUrn ? `?quick_form_urn=${encodeURIComponent(quickFormUrn)}` : '';
		return backend(`${base}/quick-form-editor/${query}`, 'GET', undefined, fetch);
	}

	return json({ error: `unknown action '${action}'` }, { status: 400 });
};

export const PATCH: RequestHandler = async ({ params, request, url, fetch }) => {
	const body = await request.json();
	return backend(
		`${BASE_API_URL}/library-drafts/${params.id}/quick-form-editor/`,
		'PUT',
		{
			quick_form_urn: url.searchParams.get('quick_form_urn') ?? undefined,
			editing_draft: body.editing_draft
		},
		fetch
	);
};
