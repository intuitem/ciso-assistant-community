import type { RequestHandler } from './$types';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/webhooks/event-types/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	const optionsResponse = await res.json();

	const options = optionsResponse.map((eventType: string) => {
		const [modelName, action] = eventType.split('.');
		return {
			id: eventType,
			name: action,
			model_name: modelName
		};
	});

	return new Response(JSON.stringify(options), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
