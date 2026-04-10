import { ALLAUTH_API_URL, BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import {
	activateTOTPSchema,
	registerWebAuthnSchema
} from '../(internal)/my-profile/settings/mfa/utils/schemas';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';
import { setFlash } from 'sveltekit-flash-message/server';

export const load: PageServerLoad = async (event) => {
	// SSO-only users should not set up local MFA — it won't protect their SSO login
	if (event.locals.user?.is_sso && !event.locals.user?.is_local) {
		redirect(302, '/');
	}

	const authenticatorsEndpoint = `${ALLAUTH_API_URL}/account/authenticators`;
	const authenticatorsResponse = await event
		.fetch(authenticatorsEndpoint)
		.then((res) => res.json());

	if (authenticatorsResponse.status === 200) {
		const authenticators = authenticatorsResponse.data;
		if (
			Array.isArray(authenticators) &&
			authenticators.some((auth) => auth.type === 'totp' || auth.type === 'webauthn')
		) {
			redirect(302, '/');
		}
	}

	const totpEndpoint = `${authenticatorsEndpoint}/totp`;
	const totpResponse = await event.fetch(totpEndpoint).then((res) => res.json());
	const totp = totpResponse.meta;

	let webauthnCreationOptions = null;
	try {
		const webauthnEndpoint = `${ALLAUTH_API_URL}/account/authenticators/webauthn`;
		const webauthnRes = await event.fetch(webauthnEndpoint);
		if (webauthnRes.ok) {
			const webauthnData = await webauthnRes.json();
			webauthnCreationOptions = webauthnData.data?.creation_options ?? null;
		}
	} catch {
		console.error('Could not fetch WebAuthn creation options');
	}

	const activateTOTPForm = await superValidate(zod(activateTOTPSchema));
	const registerWebAuthnForm = await superValidate(zod(registerWebAuthnSchema));

	return {
		totp,
		activateTOTPForm,
		webauthnCreationOptions,
		registerWebAuthnForm,
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
	},
	registerWebAuthn: async (event) => {
		const formData = await event.request.formData();
		if (!formData) return fail(400, { error: 'No form data' });

		const form = await superValidate(formData, zod(registerWebAuthnSchema));
		if (!form.valid) return fail(400, { form });

		const credentialJson = formData.get('credential');
		if (!credentialJson || typeof credentialJson !== 'string') {
			return fail(400, { error: 'Missing credential' });
		}

		let credential;
		try {
			credential = JSON.parse(credentialJson);
		} catch {
			return fail(400, { error: 'Invalid credential' });
		}

		const endpoint = `${ALLAUTH_API_URL}/account/authenticators/webauthn`;
		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify({ name: form.data.name, credential })
		};

		let response;
		try {
			const res = await event.fetch(endpoint, requestInitOptions);
			response = await res.json();
		} catch {
			return fail(502, { error: 'Could not register WebAuthn credential' });
		}

		if (response.status !== 200) {
			console.error('Could not register WebAuthn credential');
			if (Object.hasOwn(response, 'errors')) {
				response.errors.forEach((error: { param: string; message: string }) => {
					setError(form, error.param as any, error.message);
				});
			}
			return fail(response.status, { form });
		}

		// Revoke all user sessions (except the one which registered the key)
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

		setFlash({ type: 'success', message: m.successfullyAddedSecurityKey() }, event);
		redirect(302, '/');
	}
};
