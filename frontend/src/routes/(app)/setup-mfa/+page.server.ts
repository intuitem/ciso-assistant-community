import { ALLAUTH_API_URL, BASE_API_URL } from '$lib/utils/constants';
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { activateTOTPSchema } from '../(internal)/my-profile/settings/mfa/utils/schemas';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';
import { setFlash } from 'sveltekit-flash-message/server';

export const load: PageServerLoad = async (event) => {
	const authenticatorsEndpoint = `${ALLAUTH_API_URL}/account/authenticators`;
	const authenticatorsResponse = await event
		.fetch(authenticatorsEndpoint)
		.then((res) => res.json());

	if (authenticatorsResponse.status === 200) {
		const authenticators = authenticatorsResponse.data;
		if (Array.isArray(authenticators) && authenticators.find((auth) => auth.type === 'totp')) {
			redirect(302, '/');
		}
	}

	const totpEndpoint = `${authenticatorsEndpoint}/totp`;
	const totpResponse = await event.fetch(totpEndpoint).then((res) => res.json());
	const totp = totpResponse.meta;

	const activateTOTPForm = await superValidate(zod(activateTOTPSchema));

	return {
		totp,
		activateTOTPForm,
		title: m.setupMfa()
	};
};

export const actions: Actions = {
	activateTOTP: async (event) => {
		const formData = await event.request.formData();
		if (!formData) return fail(400, { error: 'No form data' });

		const form = await superValidate(formData, zod(activateTOTPSchema));
		if (!form.valid) return fail(400, { form });

		const endpoint = `${ALLAUTH_API_URL}/account/authenticators/totp`;
		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);
		const data = await response.json();

		if (data.status !== 200) {
			console.error('Could not activate TOTP', data);
			if (Object.hasOwn(data, 'errors')) {
				data.errors.forEach((error: { param: string; code: string; message: string }) => {
					setError(form, error.param, error.message);
				});
			}
			return fail(data.status, { form });
		}

		// Revoke all user sessions (except the one which activated the TOTP)
		try {
			const revokeResponse = await event.fetch(`${BASE_API_URL}/iam/revoke-sessions/`, {
				method: 'POST'
			});
			if (!revokeResponse.ok) {
				console.error('Failed to revoke other sessions', await revokeResponse.text());
			}
		} catch (error) {
			console.error('Error revoking other sessions', error);
		}

		setFlash({ type: 'success', message: m.successfullyActivatedTOTP() }, event);
		redirect(302, '/');
	}
};
