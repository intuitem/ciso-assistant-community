import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const params = url.searchParams.toString();
	const res = await fetch(`${BASE_API_URL}/saved-filters/${params ? '?' + params : ''}`);
	if (!res.ok) {
		error(res.status, await res.json());
	}
	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
	});
};

export const POST: RequestHandler = async ({ fetch, request }) => {
	const res = await fetch(`${BASE_API_URL}/saved-filters/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
