import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request }) => {
	const response = await fetch(`${BASE_API_URL}/settings/mailer/test/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
	return new Response(await response.text(), {
		status: response.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
