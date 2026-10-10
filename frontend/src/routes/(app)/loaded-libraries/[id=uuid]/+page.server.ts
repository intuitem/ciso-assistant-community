import { BASE_API_URL } from '$lib/utils/constants';
import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';

export const actions: Actions = {
	update: async (event) => {
		const action = new URL(event.request.url).searchParams.get('action');
		const endpoint =
			`${BASE_API_URL}/loaded-libraries/${event.params.id}/update` +
			(action ? `?action=${action}` : '');
		const res = await event.fetch(endpoint); // We will have to make this a PATCH later (we should use PATCH when modifying an object)
		const result = await res.json();

		if (!res.ok) {
			if (result.error === 'score_change_detected') {
				return fail(409, {
					error: 'score_change_detected',
					choices: result.strategies
				});
			}
			setFlash(
				{
					type: 'error',
					message: safeTranslate(result.error)
				},
				event
			);
		} else {
			setFlash(
				{
					type: 'success',
					message: m.librarySuccessfullyUpdated()
				},
				event
			);
		}
	}
};
