import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async (event) => {
	const requestInitOptions: RequestInit = {
		method: 'POST'
	};

	const dryRun = event.url.searchParams.get('dry_run') !== 'false';

	const endpoint = `${BASE_API_URL}/applied-controls/${event.params.id}/sync-to-reference-control/?dry_run=${dryRun}`;
	const res = await event.fetch(endpoint, requestInitOptions);
	const responseData = await res.json();

	if (!res.ok) {
		console.error(responseData);
	}

	return new Response(JSON.stringify(responseData), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
