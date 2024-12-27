import { BASE_API_URL } from '$lib/utils/constants';
import { safeTranslate } from '$lib/utils/i18n';
import { ResetPasswordSchema } from '$lib/utils/schemas';
import * as m from '$paraglide/messages';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import { setLanguageTag } from '$paraglide/runtime';
import { DEFAULT_LANGUAGE } from '$lib/utils/constants';

export const load: PageServerLoad = async (event) => {
	setLanguageTag(event.cookies.get('ciso_lang') || DEFAULT_LANGUAGE);
	const form = await superValidate(event.request, zod(ResetPasswordSchema));

	return { form };
};

export const actions: Actions = {
	default: async (event) => {
		const form = await superValidate(event.request, zod(ResetPasswordSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const endpoint = `${BASE_API_URL}/iam/password-reset/confirm/`;
		form.data.token = event.url.searchParams.get('token');
		form.data.uidb64 = event.url.searchParams.get('uidb64');
		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			if (response.new_password) {
				setError(form, 'new_password', response.new_password);
			}
			if (response.confirm_new_password) {
				setError(form, 'confirm_new_password', response.confirm_new_password);
			}
			if (response.error) {
				setFlash({ type: 'error', message: safeTranslate(response.error) }, event);
				redirect(302, '/login');
			}
			return fail(400, { form });
		}

		setFlash({ type: 'success', message: m.passwordSuccessfullyReset() }, event);
		redirect(302, '/login');
	}
};
