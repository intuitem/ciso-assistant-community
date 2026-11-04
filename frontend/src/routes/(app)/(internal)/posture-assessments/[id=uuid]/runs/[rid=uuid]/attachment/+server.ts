import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(
		`${BASE_API_URL}/automation/posture-assessments/${params.id}/runs/${params.rid}/attachment/`
	);
	if (!res.ok) {
		// the backend answers a missing attachment with a bodyless 404
		const body = await res.text();
		let detail: Omit<App.Error, 'status'> = { message: 'attachment not found' };
		try {
			if (body) detail = JSON.parse(body);
		} catch {
			detail = { message: body };
		}
		errorFromBody(res.status, detail);
	}
	return new Response(res.body, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/octet-stream',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
