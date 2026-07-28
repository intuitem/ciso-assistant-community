import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(
		`${BASE_API_URL}/automation/posture-assessments/${params.id}/runs/${params.rid}/attachment/`
	);
	if (!res.ok) {
		// the backend answers a missing attachment with a bodyless 404
		const body = await res.text();
		let detail: App.Error = { message: 'attachment not found' };
		try {
			if (body) detail = JSON.parse(body);
		} catch {
			detail = { message: body };
		}
		error(res.status as NumericRange<400, 599>, detail);
	}
	return new Response(res.body, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/octet-stream',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? 'attachment'
		}
	});
};
