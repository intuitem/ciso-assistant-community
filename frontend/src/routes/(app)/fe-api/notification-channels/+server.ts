import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const endpoint = `${BASE_API_URL}/notification-channels/`;

export const GET: RequestHandler = async ({ fetch }) => {
	const res = await fetch(endpoint);
	if (!res.ok) error(res.status, 'Error fetching notification channels');
	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
	});
};

export const POST: RequestHandler = async ({ fetch, request }) => {
	const res = await fetch(endpoint, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(await request.json())
	});
	// The matrix rejects a combination the registry forbids; pass the reason through
	// rather than letting the switch spring back unexplained.
	const body = await res.json();
	if (!res.ok) error(res.status, body?.error ?? 'Error updating notification channel');
	return new Response(JSON.stringify(body), {
		headers: { 'Content-Type': 'application/json' }
	});
};
