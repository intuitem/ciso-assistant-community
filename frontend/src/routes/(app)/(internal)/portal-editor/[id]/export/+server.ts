import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, fetch }) => {
	const res = await fetch(`${BASE_API_URL}/portals/${params.id}/export/`);
	if (!res.ok) {
		const status = res.status >= 400 && res.status <= 599 ? res.status : 502;
		error(status as NumericRange<400, 599>, await res.text());
	}

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/x-yaml',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
