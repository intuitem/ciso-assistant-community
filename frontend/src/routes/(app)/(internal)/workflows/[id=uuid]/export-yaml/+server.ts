import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, fetch }) => {
	const endpoint = `${BASE_API_URL}/workflows/workflows/${params.id}/export-yaml/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error exporting the workflow');
	}

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/x-yaml',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
