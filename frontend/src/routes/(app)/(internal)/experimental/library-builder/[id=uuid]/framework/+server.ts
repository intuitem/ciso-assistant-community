import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * Adapter speaking the FrameworkBuilder `_action` protocol against a
 * framework object stored *inside* a LibraryDraft document. There is no
 * second draft layer: the document is the work-in-progress, so
 * start-editing/save-draft read and write the document directly. Publishing
 * is not an editor concern — it happens on the library page.
 */

async function backend(url: string, method: string, body: unknown, fetchFn: typeof fetch) {
	const r = await fetchFn(url, {
		method,
		headers: { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	const text = await r.text();
	return { status: r.status, data: text ? JSON.parse(text) : null };
}

export const POST: RequestHandler = async ({ params, request, url, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body._action;
	const frameworkUrn = url.searchParams.get('framework_urn') ?? undefined;
	const base = `${BASE_API_URL}/library-drafts/${params.id}`;

	if (action === 'start-editing') {
		const query = frameworkUrn ? `?framework_urn=${encodeURIComponent(frameworkUrn)}` : '';
		const { status, data } = await backend(
			`${base}/framework-editor/${query}`,
			'GET',
			undefined,
			fetch
		);
		return json(data, { status });
	}

	return json({ error: `unknown action '${action}'` }, { status: 400 });
};

export const PATCH: RequestHandler = async ({ params, request, url, fetch }) => {
	const body = await request.json();
	const { status, data } = await backend(
		`${BASE_API_URL}/library-drafts/${params.id}/framework-editor/`,
		'PUT',
		{
			framework_urn: url.searchParams.get('framework_urn') ?? undefined,
			editing_draft: body.editing_draft
		},
		fetch
	);
	return json(data, { status });
};
