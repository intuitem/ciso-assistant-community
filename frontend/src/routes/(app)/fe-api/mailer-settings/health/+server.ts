import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const response = await fetch(`${BASE_API_URL}/settings/mailer/health/`);
	return new Response(await response.text(), {
		status: response.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
