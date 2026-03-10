import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { ResetMFASchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { setFlash } from 'sveltekit-flash-message/server';
import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import { zod } from 'sveltekit-superforms/adapters';

export const load: PageServerLoad = async (event) => {
	const form = await superValidate(event.request, zod(ResetMFASchema));

	return { form, title: m.resetMFA() };
};

export const actions: Actions = {
	default: async (event) => {
		const form = await superValidate(event.request, zod(ResetMFASchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const endpoint = `${BASE_API_URL}/iam/reset-mfa/`;

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			return fail(res.status, { form });
		}

		setFlash({ type: 'success', message: m.mfaSuccessfullyReset() }, event);
		redirect(302, '/users');
	}
};
