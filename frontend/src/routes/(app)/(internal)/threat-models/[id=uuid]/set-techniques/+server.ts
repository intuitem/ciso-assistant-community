import { BASE_API_URL } from '$lib/utils/constants';
import { json, type RequestHandler } from '@sveltejs/kit';

export const POST: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json();
	const res = await fetch(`${BASE_API_URL}/threat-models/${params.id}/set-techniques/`, {
		method: 'POST',
		body: JSON.stringify(body)
	});
	return json(await res.json(), { status: res.status });
};
