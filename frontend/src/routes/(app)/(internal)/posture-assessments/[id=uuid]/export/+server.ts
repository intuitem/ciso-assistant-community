import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const res = await fetch(
		`${BASE_API_URL}/automation/posture-assessments/${params.id}/export-results/${url.search}`
	);
	if (!res.ok) {
		errorFromBody(res.status, await res.json());
	}
	return new Response(res.body, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/octet-stream',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
