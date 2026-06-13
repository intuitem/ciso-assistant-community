import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

async function fetchJson(fetch: typeof globalThis.fetch, endpoint: URL) {
	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	return res.json();
}

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const catalogueUrl = new URL(`${BASE_API_URL}/policies/${params.id}/control-catalogue/`);
	for (const [key, value] of url.searchParams.entries()) {
		catalogueUrl.searchParams.append(key, value);
	}

	return json(await fetchJson(fetch, catalogueUrl));
};
