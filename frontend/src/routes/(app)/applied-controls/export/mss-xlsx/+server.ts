import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const queryString = url.searchParams.toString();
	const endpoint = `${BASE_API_URL}/applied-controls/mss_xlsx/${queryString ? '?' + queryString : ''}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.text());
	}

	const fileName = `applied-controls-mss-${new Date().toISOString().split('T')[0]}.xlsx`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
