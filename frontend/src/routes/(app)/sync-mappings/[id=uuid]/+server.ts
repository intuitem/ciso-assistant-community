import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/integrations/sync-mappings/${params.id}/`;

	const requestInitOptions: RequestInit = {
		method: 'DELETE'
	};

	const res = await fetch(endpoint, requestInitOptions);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.text());
	}
	return new Response(null, {
		status: 204
	});
};
