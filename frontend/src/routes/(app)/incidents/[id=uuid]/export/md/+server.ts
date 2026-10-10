import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'incidents';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/md/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the MD file');
	}

	const fileName = `incident-${params.id}.md`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'text/markdown',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
