import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch }) => {
	const response = await fetch(`${BASE_API_URL}/settings/general/force_date_format/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' }
	});

	let data;
	try {
		data = await response.json();
	} catch {
		return Response.json(
			{ error: 'unexpectedResponseFromServer' },
			{ status: response.status || 500 }
		);
	}

	return Response.json(data, { status: response.status });
};
