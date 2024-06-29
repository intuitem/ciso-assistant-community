import { BASE_API_URL, URN_REGEX } from '$lib/utils/constants';

import { fail, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';

export const actions: Actions = {
	add_evidence: async (event) => {
		const endpoint = `${BASE_API_URL}/applied-controls/${event.params.id}/add_evidence/`;
		const formData = await event.request.formData();

		const evidence = formData.get('evidence');
		const res = await event.fetch(endpoint, {
			method: 'POST',
			body: JSON.stringify({ evidence }),
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (!res.ok) {
			setFlash({ type: 'error', message: 'Some Localized Error Message' }, event);
			const errorText = await res.text();
			fail(res.status, {
				message: errorText
			});
		}

		setFlash({ type: 'success', message: 'Some localized success message.' }, event);
	},
	remove_evidence: async (event) => {
		const endpoint = `${BASE_API_URL}/applied-controls/${event.params.id}/remove_evidence/`;
		const formData = await event.request.formData();

		const evidence = formData.get('evidence');
		const res = await event.fetch(endpoint, {
			method: 'POST',
			body: JSON.stringify({ evidence }),
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (!res.ok) {
			setFlash({ type: 'error', message: 'Some Localized Error Message' }, event);
			const errorText = await res.text();
			fail(res.status, {
				message: errorText
			});
		}

		setFlash({ type: 'success', message: 'Some localized success message.' }, event);
	}
};
