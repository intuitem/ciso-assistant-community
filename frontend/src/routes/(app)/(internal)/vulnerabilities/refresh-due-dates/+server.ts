import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/vulnerabilities/refresh-due-dates/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' }
	});

	const data = await res.json();
	return json(data, { status: res.status });
};
