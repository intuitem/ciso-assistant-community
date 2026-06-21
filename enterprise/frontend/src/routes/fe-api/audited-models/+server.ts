import { BASE_API_URL } from '$lib/utils/constants';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const response = await fetch(`${BASE_API_URL}/audited-models/`);

	if (!response.ok) {
		throw error(response.status, await response.text());
	}

	return json(await response.json());
};
