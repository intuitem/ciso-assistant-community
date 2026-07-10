import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/resilience/dora-incident-reports/${params.id}/export_json/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the DORA IR JSON export');
	}

	const fileName = `dora-ir-${params.id}.json`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/json',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
