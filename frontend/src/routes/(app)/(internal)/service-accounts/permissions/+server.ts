import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/iam/service-accounts/permissions/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	return new Response(JSON.stringify(await res.json()), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
