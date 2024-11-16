import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/risk-acceptances/waiting/`;
	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching waiting risk acceptance');
	}

	const riskAcceptances = await res.json();
	return new Response(JSON.stringify(riskAcceptances), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
