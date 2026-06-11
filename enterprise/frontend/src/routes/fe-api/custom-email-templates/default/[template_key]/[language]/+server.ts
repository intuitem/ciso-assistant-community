import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/custom-email-templates/default/${params.template_key}/${params.language}/`;
	const res = await fetch(endpoint);
	const responseData = await res.text();

	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};
