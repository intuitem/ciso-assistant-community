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
	},
	update: async (event) => {
		const endpoint = `${BASE_API_URL}/loaded-libraries/${event.params.id}/update/`;
		const res = await event.fetch(endpoint); // We will have to make this a PATCH later (we should use PATCH when modifying an object)
		const resText: string = await res.text().then((text) => text.substring(1, text.length - 1)); // To remove the double quotes around the message, django add double quotes for no reason, we can make this cleaner later

		if (!res.ok) {
			setFlash(
				{
					type: 'error',
					message: safeTranslate(resText)
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
