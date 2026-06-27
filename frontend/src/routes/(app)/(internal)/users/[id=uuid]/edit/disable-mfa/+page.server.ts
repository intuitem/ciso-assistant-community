import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { setFlash } from 'sveltekit-flash-message/server';
import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const objectEndpoint = `${BASE_API_URL}/users/${params.id}/object/`;
	const object = await fetch(objectEndpoint).then((res) => res.json());
	return { object, title: m.disableMFA() };
};

export const actions: Actions = {
	default: async (event) => {
		const endpoint = `${BASE_API_URL}/iam/disable-mfa/`;

		const res = await event.fetch(endpoint, {
			method: 'POST',
			body: JSON.stringify({ user: event.params.id })
		});

		if (!res.ok) {
			let payload: Record<string, unknown> = {};
			try {
				payload = await res.json();
			} catch (err) {
				console.warn('disable-mfa: backend returned a non-JSON error body', err);
			}
			const errorKey = typeof payload.error === 'string' ? payload.error : 'errorDisablingMFA';
			setFlash({ type: 'error', message: safeTranslate(errorKey) }, event);
			return fail(res.status, { error: errorKey });
		}

		setFlash({ type: 'success', message: m.mfaDisabledSuccessfully() }, event);
		redirect(302, `/users/${event.params.id}`);
	}
};
