import { BASE_API_URL } from '$lib/utils/constants';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import * as m from '$paraglide/messages';
import { localItems } from '$lib/utils/locales';
import { languageTag } from '$paraglide/runtime';

export const actions: Actions = {
	load: async (event) => {
		const endpoint = `${BASE_API_URL}/stored-libraries/${event.params.id}/import`;
		const res = await event.fetch(endpoint); // We will have to make this a POST later (we should use POST when creating a new object)
		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			setFlash({ type: 'error', message: response.error }, event);
			return fail(400, { error: m.errorImportingLibrary() });
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
					message: localItems(languageTag())[resText]
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
