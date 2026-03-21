import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const ENDPOINT = `${BASE_API_URL}/risk-matrices`;

/** Proxy helper */
async function proxyRequest(fetchFn: typeof fetch, url: string, method: string, body?: unknown) {
	const opts: RequestInit = {
		method,
		headers: { 'Content-Type': 'application/json' }
	};
	if (body !== undefined) {
		opts.body = JSON.stringify(body);
	}
	const res = await fetchFn(url, opts);
	if (res.status === 204) return new Response(null, { status: 204 });
	const data = await res.json();
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, data);
	}
	return json(data, { status: res.status });
}

/** List all risk matrices (for refreshing drafts) */
export const GET: RequestHandler = async ({ fetch }) => {
	return proxyRequest(fetch, `${ENDPOINT}/`, 'GET');
};

/** Create a new draft matrix */
export const POST: RequestHandler = async ({ fetch, request, url }) => {
	const action = url.searchParams.get('action');

	if (action === 'import-yaml') {
		// Forward file upload as-is
		const formData = await request.formData();
		const res = await fetch(`${ENDPOINT}/import-yaml/`, {
			method: 'POST',
			body: formData
		});
		const data = await res.json();
		if (!res.ok) error(res.status as NumericRange<400, 599>, data);
		return json(data, { status: res.status });
	}

	// Default: create-draft with JSON body
	const body = await request.json();
	return proxyRequest(fetch, `${ENDPOINT}/create-draft/`, 'POST', body);
};
