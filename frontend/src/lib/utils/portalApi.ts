// Shared server-side helpers for the portal-editor route actions/loaders.
import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';

type Fetch = typeof globalThis.fetch;

// Unwrap a list/detail response, surfacing backend errors instead of masking them as
// empty results (a 403/500 should not look like "no data").
export const unwrap = async (res: Response) => {
	if (!res.ok) error(res.status, await res.text());
	const data = await res.json();
	return data.results ?? data;
};

const jsonReq =
	(method: string) =>
	(fetch: Fetch, path: string, body?: unknown): Promise<Response> =>
		fetch(`${BASE_API_URL}${path}`, {
			method,
			headers: { 'Content-Type': 'application/json' },
			body: body === undefined ? undefined : JSON.stringify(body)
		});

export const postJSON = jsonReq('POST');
export const patchJSON = jsonReq('PATCH');

export const del = (fetch: Fetch, path: string): Promise<Response> =>
	fetch(`${BASE_API_URL}${path}`, { method: 'DELETE' });
