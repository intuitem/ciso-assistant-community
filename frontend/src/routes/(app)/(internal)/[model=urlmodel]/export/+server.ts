import { BASE_API_URL } from '$lib/utils/constants';
import { URL_MODEL_MAP } from '$lib/utils/crud';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ params, fetch }) => {
	const URLModel = params.model;
	const endpointUrl = URL_MODEL_MAP[URLModel]?.endpointUrl || URLModel;
	const endpoint = `${BASE_API_URL}/${endpointUrl}/export_csv/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the CSV file');
	}

	const fileName = `${URLModel}-${new Date().toISOString()}.csv`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'text/csv',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
