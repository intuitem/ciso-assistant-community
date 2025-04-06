import { BASE_API_URL } from '$lib/utils/constants';
import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';

export const actions: Actions = {
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
