import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/webhooks/event-types/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const optionsResponse = await res.json();

	const options = optionsResponse.map((eventType: string) => {
		return { label: eventType, value: eventType };
	});

	return new Response(JSON.stringify(options), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
