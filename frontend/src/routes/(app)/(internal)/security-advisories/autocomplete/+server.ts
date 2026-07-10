import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const endpoint = `${BASE_API_URL}/security-advisories/autocomplete/${url.search}`;
	const res = await fetch(endpoint);
	const data = await res.json();
	return json(data, { status: res.status });
};
