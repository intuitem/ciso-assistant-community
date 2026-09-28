import { BASE_API_URL } from '$lib/utils/constants';
import { error, fail, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// A published form, answered without creating a response. Same evaluator as the
// draft preview, fed from the live rows.
const preview = async (fetch: typeof globalThis.fetch, id: string, answers: unknown) =>
	fetch(`${BASE_API_URL}/quick-forms/${id}/preview/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ answers })
	});

export const load: PageServerLoad = async ({ fetch, params }) => {
	const res = await preview(fetch, params.id, {});
	if (!res.ok) error(res.status, 'Could not preview this form');
	return { quickFormId: params.id, initial: await res.json() };
};

export const actions: Actions = {
	evaluate: async ({ fetch, params, request }) => {
		// A form action only accepts form-encoded bodies; `request.json()` here answers
		// 415 and the live evaluation never runs. The payload travels as one field.
		const { answers } = JSON.parse(String((await request.formData()).get('payload') ?? '{}'));
		const res = await preview(fetch, params.id, answers ?? {});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return await res.json();
	}
};
