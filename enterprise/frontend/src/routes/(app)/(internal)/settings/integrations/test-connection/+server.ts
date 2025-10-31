import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async (event) => {
	const body = await event.request.text();
	const requestInitOptions: RequestInit = {
		method: 'POST',
		body
	};

	const endpoint = `${BASE_API_URL}/integrations/test-connection/`;
	const res = await event.fetch(endpoint, requestInitOptions);

	if (!res.ok) {
		const response = await res.text();
		console.error(response);
		return new Response(JSON.stringify(response), {
			status: res.status,
			headers: {
				'Content-Type': 'application/json'
			}
		});
	}

	return new Response(JSON.stringify(await res.json()), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
