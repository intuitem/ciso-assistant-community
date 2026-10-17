import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

const endpoint = `${BASE_API_URL}/settings/mailer/`;

async function passthrough(response: Response): Promise<Response> {
	return new Response(await response.text(), {
		status: response.status,
		headers: { 'Content-Type': 'application/json' }
	});
}

export const GET: RequestHandler = async ({ fetch }) => passthrough(await fetch(endpoint));

export const PUT: RequestHandler = async ({ fetch, request }) =>
	passthrough(
		await fetch(endpoint, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: await request.text()
		})
	);
