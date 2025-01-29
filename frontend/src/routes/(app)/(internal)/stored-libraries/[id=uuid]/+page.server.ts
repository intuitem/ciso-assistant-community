import { BASE_API_URL } from '$lib/utils/constants';
import { safeTranslate } from '$lib/utils/i18n';
import * as m from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';

export const actions: Actions = {
	load: async (event) => {
		const endpoint = `${BASE_API_URL}/stored-libraries/${event.params.id}/import/`;
		const res = await event.fetch(endpoint); // We will have to make this a POST later (we should use POST when creating a new object)
		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			setFlash({ type: 'error', message: safeTranslate(response.error) }, event);
			return fail(400, { error: m.errorLoadingLibrary() });
		}
		setFlash(
			{
				type: 'success',
				message: m.librarySuccessfullyLoaded()
			},
			event
		);
	}
};
