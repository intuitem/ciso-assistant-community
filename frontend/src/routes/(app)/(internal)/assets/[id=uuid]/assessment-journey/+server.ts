import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

const TARGET = 'asset.risk_assessment';

// Where the asset stands, and the forms the caller may start to assess it.
export const GET: RequestHandler = async ({ fetch, params }) => {
	const query = new URLSearchParams({ target: TARGET, subject: params.id });
	const [journey, options] = await Promise.all([
		fetch(`${BASE_API_URL}/assets/${params.id}/assessment-journey/`).then((res) =>
			res.ok ? res.json() : null
		),
		fetch(`${BASE_API_URL}/quick-forms/assess-options/?${query}`).then((res) =>
			res.ok ? res.json() : []
		)
	]);
	return Response.json({ journey, options });
};

// Start (or resume) an assessment of this asset through one of them.
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const { kind, id } = await request.json();
	const base = kind === 'form' ? 'quick-forms' : 'quick-form-publications';
	const res = await fetch(`${BASE_API_URL}/${base}/${id}/start/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ subject: params.id })
	});
	const body = await res.json().catch(() => ({}));
	// A new framing starts from the last applied one's answers.
	const responseId = res.ok && !body.resumed ? body.redirect?.split('/').pop() : undefined;
	if (responseId) {
		await fetch(`${BASE_API_URL}/assets/${params.id}/assessment-journey/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ response: responseId })
		}).catch(() => {});
	}
	return Response.json(body, { status: res.status });
};
