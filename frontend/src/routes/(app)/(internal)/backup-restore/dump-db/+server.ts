import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/serdes/dump-db/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the dump file');
	}

	const fileName = `backup-${new Date().toISOString()}.bak`;
	// the filename is only informative, as is not used by the browser
	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/gzip',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
