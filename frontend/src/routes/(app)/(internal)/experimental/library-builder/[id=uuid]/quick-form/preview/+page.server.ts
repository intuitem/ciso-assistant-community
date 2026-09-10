import { BASE_API_URL } from '$lib/utils/constants';
import { error, fail, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// The preview renders the *saved* draft: the builder saves explicitly (Ctrl+S), so
// unsaved edits are not visible here. Said plainly on the page rather than guessed at.
const preview = async (
	fetch: typeof globalThis.fetch,
	id: string,
	urn: string,
	answers: Record<string, unknown>
) =>
	fetch(`${BASE_API_URL}/library-drafts/${id}/quick-form-fill-preview/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ quick_form_urn: urn, answers })
	});

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const urn = url.searchParams.get('quick_form_urn') ?? '';
	const res = await preview(fetch, params.id, urn, {});
	if (!res.ok) error(res.status, 'Could not preview this form');
	return { draftId: params.id, quickFormUrn: urn, initial: await res.json() };
};

export const actions: Actions = {
	evaluate: async ({ fetch, params, request }) => {
		const { urn, answers } = await request.json();
		const res = await preview(fetch, params.id, urn, answers ?? {});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return await res.json();
	}
};
