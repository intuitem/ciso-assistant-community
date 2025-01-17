import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/folders/${params.id}/export/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the dump file');
	}

	const fileName = `ciso-assistant-domain-export-${new Date().toISOString()}.bak`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/zip',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
