import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const size = url.searchParams.get('size') ?? '4';
	const res = await fetch(
		`${BASE_API_URL}/ebios-rm/studies/rating-kit-defaults/?size=${encodeURIComponent(size)}`
	);
	if (!res.ok) error(res.status as NumericRange<400, 599>, await res.text());
	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
	});
};
