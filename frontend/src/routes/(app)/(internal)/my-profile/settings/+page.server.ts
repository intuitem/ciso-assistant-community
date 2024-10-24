import { ALLAUTH_API_URL } from '$lib/utils/constants';
import { fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { activateTOTPSchema } from './mfa/utils/schemas';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';

export const load: PageServerLoad = async (event) => {
	const authenticatorsEndpoint = `${ALLAUTH_API_URL}/account/authenticators`;
	const authenticatorsResponse = await event.fetch(authenticatorsEndpoint);
	if (!authenticatorsResponse.ok) {
		const response = await authenticatorsResponse.json();
		console.error('Could not get authenticators', response);
		fail(response.status, { error: 'Could not get authenticators' });
	}
	const authenticators = await authenticatorsResponse.json().then((res) => res.data);
	console.debug('authenticators', authenticators);

	const totpEndpoint = `${authenticatorsEndpoint}/totp`;
	const totpResponse = await event.fetch(totpEndpoint).then((res) => res.json());
	const totp = totpResponse.meta;
	console.debug('totp', totp);

	const activateTOTPForm = await superValidate(zod(activateTOTPSchema));

	return { authenticators, totp, activateTOTPForm };
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

		console.debug('requestInitOptions', requestInitOptions);

		const response = await event.fetch(endpoint, requestInitOptions);
		if (!response.ok) {
			const data = await response.json();
			console.error('Could not activate TOTP', data);
			return fail(data.status, { error: data });
		}

		const data = await response.json();

		if (data.status !== 200) {
			console.error('Could not activate TOTP', data);
			if (Object.hasOwn(data, 'errors')) {
				data.errors.forEach((error) => {
					setError(form, error.param, error.message);
				});
			}
			return fail(data.status, { form });
		}

		console.debug('Activated TOTP', data);
		setFlash({ type: 'success', message: '_successfullyActivatedTOTP' }, event);
		return { form };
	},
	deactivateTOTP: async (event) => {
		throw new Error('Not implemented');
	},
	regenerateRecoveryCodes: async (event) => {
		throw new Error('Not implemented');
	}
};
