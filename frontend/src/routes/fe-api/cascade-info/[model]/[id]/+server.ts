import { BASE_API_URL } from '$lib/utils/constants';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, fetch }) => {
	const { model, id } = params;

	const endpoint = `${BASE_API_URL}/${model}/${id}/cascade-info/`;
	const response = await fetch(endpoint);

	if (!response.ok) {
		throw error(response.status, await response.text());
	}

	return json(await response.json());
};
