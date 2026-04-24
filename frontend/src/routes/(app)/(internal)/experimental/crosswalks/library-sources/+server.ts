import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/crosswalks/library-sources/`);
	const data = await res.json();
	if (!res.ok) error(res.status as NumericRange<400, 599>, data);
	return json(data);
};
