import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, fetch }) => {
	const endpoint = `${BASE_API_URL}/workflows/workflows/${params.id}/export-yaml/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		// Forward the backend's status (403/404/…) instead of flattening to 400.
		const status = res.status >= 400 && res.status <= 599 ? res.status : 502;
		error(status as NumericRange<400, 599>, 'Error exporting the workflow');
	}

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/x-yaml',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
