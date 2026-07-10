import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ENDPOINT = `${BASE_API_URL}/risk-matrices`;

async function proxyPost(fetchFn: typeof fetch, url: string, body?: unknown) {
	const opts: RequestInit = {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' }
	};
	if (body !== undefined) opts.body = JSON.stringify(body);
	const res = await fetchFn(url, opts);
	const data = await res.json();
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data, { status: res.status });
}

/** GET — export-yaml */
export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const action = url.searchParams.get('action');
	if (action === 'export-yaml') {
		const res = await fetch(`${ENDPOINT}/${params.id}/export-yaml/`);
		if (!res.ok) {
			const data = await res.json();
			error(res.status as NumericRange<400, 599>, data);
		}
		const yamlContent = await res.text();
		return new Response(yamlContent, {
			status: 200,
			headers: {
				'Content-Type': 'application/x-yaml',
				'Content-Disposition':
					res.headers.get('Content-Disposition') || 'attachment; filename="matrix.yaml"'
			}
		});
	}
	error(400, { error: 'Invalid action' });
};

/** PATCH — save editing_draft */
export const PATCH: RequestHandler = async ({ fetch, request, params }) => {
	const body = await request.json();
	const res = await fetch(`${ENDPOINT}/${params.id}/save-draft/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	const data = await res.json();
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data, { status: res.status });
};

/** POST — action dispatcher (start-editing, publish-draft, discard-draft) */
export const POST: RequestHandler = async ({ fetch, request, params, url }) => {
	const action = url.searchParams.get('action');
	if (
		!action ||
		!['start-editing', 'publish-draft', 'discard-draft', 'create-draft-from'].includes(action)
	) {
		error(400, {
			error:
				'Invalid action. Use ?action=start-editing|publish-draft|discard-draft|create-draft-from'
		});
	}
	return proxyPost(fetch, `${ENDPOINT}/${params.id}/${action}/`);
};

/** DELETE — delete the matrix */
export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${ENDPOINT}/${params.id}/`, { method: 'DELETE' });
	if (!res.ok && res.status !== 204) {
		const data = await res.json();
		error(res.status as NumericRange<400, 599>, data);
	}
	return new Response(null, { status: 204 });
};
