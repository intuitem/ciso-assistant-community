import { BASE_API_URL } from '$lib/utils/constants';
import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import * as m from '$paraglide/messages';

export const actions: Actions = {
	default: async (event) => {
		const endpoint = `${BASE_API_URL}/stored-libraries/${event.params.id}/import`;
		const res = await event.fetch(endpoint);
		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			setFlash({ type: 'error', message: response.error }, event);
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
