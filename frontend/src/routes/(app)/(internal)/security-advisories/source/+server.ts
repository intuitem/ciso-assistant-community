import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const endpoint = `${BASE_API_URL}/security-advisories/source/${url.search}`;
	const res = await fetch(endpoint);
	const data = await res.json();
	const options =
		typeof Object.values(data)[0] === 'string'
			? Object.keys(data).map((key) => ({ label: data[key], value: key }))
			: data;
	return json(options, { status: res.status });
};
