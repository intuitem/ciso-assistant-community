import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const body = await request.json().catch(() => ({}));
	const res = await fetch(
		`${BASE_API_URL}/chat/questionnaire-questions/${params.questionId}/retry-with-control/`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		}
	);
	const data = await res.json().catch(() => ({}));
	return Response.json(data, { status: res.status });
};
