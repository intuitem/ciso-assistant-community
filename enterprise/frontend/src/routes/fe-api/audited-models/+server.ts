import { BASE_API_URL } from '#lib/utils/constants.js';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const response = await fetch(`${BASE_API_URL}/audited-models/`);

	if (!response.ok) {
		throw error(response.status, await response.text());
	}

	return Response.json(await response.json());
};
