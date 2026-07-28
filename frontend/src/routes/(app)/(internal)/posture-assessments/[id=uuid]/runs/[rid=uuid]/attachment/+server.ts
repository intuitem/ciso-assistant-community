import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(
		`${BASE_API_URL}/automation/posture-assessments/${params.id}/runs/${params.rid}/attachment/`
	);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	return new Response(res.body, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/octet-stream',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
