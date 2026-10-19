import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const params = new URLSearchParams({
		definition: url.searchParams.get('definition') ?? '',
		folder: url.searchParams.get('folder') ?? ''
	});
	const res = await fetch(`${BASE_API_URL}/metrology/metric-instances/input-candidates/?${params}`);
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
