import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(
		`${BASE_API_URL}/chat/questionnaire-questions/${params.questionId}/suggest-control/`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: '{}'
		}
	);
	const data = await res.json().catch(() => ({}));
	return Response.json(data, { status: res.status });
};
