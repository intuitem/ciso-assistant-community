import { ALLAUTH_API_URL, BASE_API_URL } from '$lib/utils/constants';
import { error, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { activateTOTPSchema, registerWebAuthnSchema } from './mfa/utils/schemas';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import { safeTranslate } from '$lib/utils/i18n';
import { z } from 'zod';
import { AuthTokenCreateSchema } from '$lib/utils/schemas';

export const load: PageServerLoad = async (event) => {
	const authenticatorsEndpoint = `${ALLAUTH_API_URL}/account/authenticators`;
	const authenticatorsResponse = await event
		.fetch(authenticatorsEndpoint)
		.then((res) => res.json());
	if (authenticatorsResponse.status !== 200) {
		console.error('Could not get authenticators', authenticatorsResponse);
		throw error(authenticatorsResponse.status, 'Could not get authenticators');
	}
	const authenticators = authenticatorsResponse.data;

	let totp = null;
	let recoveryCodes = null;

	const totpEndpoint = `${authenticatorsEndpoint}/totp`;
	const totpResponse = await event.fetch(totpEndpoint).then((res) => res.json());
	totp = totpResponse.meta;

	if (
		Array.isArray(authenticators) &&
		authenticators.find((auth) => auth.type === 'recovery_codes')
	) {
		const recoveryCodesEndpoint = `${authenticatorsEndpoint}/recovery-codes`;
		const recoveryCodesResponse = await event
			.fetch(recoveryCodesEndpoint)
			.then((res) => res.json());
		if (recoveryCodesResponse.status === 200) {
			recoveryCodes = recoveryCodesResponse.data;
		}
	}

	const webauthnCredentials = Array.isArray(authenticators)
		? authenticators.filter((auth: { type: string }) => auth.type === 'webauthn')
		: [];

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
	const personalAccessTokenCreateForm = await superValidate(zod(AuthTokenCreateSchema));
	const personalAccessTokenDeleteForm = await superValidate(zod(z.object({ id: z.string() })));
	const PATAllowed = !event.locals.user.is_third_party;
	let personalAccessTokens = [];

	if (PATAllowed) {
		const personalAccessTokensEndpoint = `${BASE_API_URL}/iam/auth-tokens/`;
		const personalAccessTokensResponse = await event.fetch(personalAccessTokensEndpoint);
		if (!personalAccessTokensResponse.ok) {
			console.error('Could not get personal access tokens', personalAccessTokensResponse);
			throw error(personalAccessTokensResponse.status, 'Could not get personal access tokens');
		}
		personalAccessTokens = await personalAccessTokensResponse.json();
	}

	return {
		authenticators,
		totp,
		activateTOTPForm,
		recoveryCodes,
		webauthnCredentials,
		webauthnCreationOptions,
		registerWebAuthnForm,
		PATAllowed,
		personalAccessTokens,
		personalAccessTokenCreateForm,
		personalAccessTokenDeleteForm,
		title: m.settings()
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
				data.errors.forEach((error) => {
					console.log('error', error.param, safeTranslate(error.code));
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
		return { form };
	},
	deactivateTOTP: async (event) => {
		const formData = await event.request.formData();
		if (!formData) return fail(400, { error: 'No form data' });

		const form = await superValidate(
			formData,
			zod(
				z.object({
					any: z.any()
				})
			)
		);

		const endpoint = `${ALLAUTH_API_URL}/account/authenticators/totp`;
		const requestInitOptions: RequestInit = {
			method: 'DELETE'
		};

		const response = await event.fetch(endpoint, requestInitOptions).then((res) => res.json());
		if (response.status !== 200) {
			console.error('Could not deactivate TOTP', response);
			return fail(response.status, { error: 'Could not deactivate TOTP' });
		}

		setFlash({ type: 'success', message: m.successfullyDeactivatedTOTP() }, event);
		return { form };
	},
	regenerateRecoveryCodes: async (event) => {
		const recoveryCodesEndpoint = `${ALLAUTH_API_URL}/account/authenticators/recovery-codes`;
		const requestInitOptions: RequestInit = {
			method: 'POST'
		};

		const response = await event
			.fetch(recoveryCodesEndpoint, requestInitOptions)
			.then((res) => res.json());

		if (response.status !== 200) {
			console.error('Could not regenerate recovery codes', response);
			setFlash({ type: 'error', message: m.errorRegeneratingRecoveryCodes() }, event);
			return fail(response.status, { error: 'Could not regenerate recovery codes' });
		}

		return { recoveryCodes: response.data };
	},
	createPAT: async (event) => {
		const PATAllowed = !event.locals.user.is_third_party;
		if (!PATAllowed) {
			return fail(403, { error: 'Forbidden' });
		}

		const formData = await event.request.formData();
		if (!formData) return fail(400, { error: 'No form data' });

		const form = await superValidate(formData, zod(AuthTokenCreateSchema));
		if (!form.valid) return fail(400, { form });

		const endpoint = `${BASE_API_URL}/iam/auth-tokens/`;
		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) {
			console.error('Could not create PAT');
			try {
				const errorResponse = await response.json();
				const errorMessage = errorResponse?.error || m.errorCreatingPersonalAccessToken();
				setFlash({ type: 'error', message: safeTranslate(errorMessage) }, event);
			} catch (e) {
				setFlash({ type: 'error', message: m.errorCreatingPersonalAccessToken() }, event);
			}
			return fail(response.status, { form });
		}

		const data = await response.json();
		return message(form, { status: response.status, data });
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

		setFlash({ type: 'success', message: m.successfullyAddedSecurityKey() }, event);
		return { form };
	},
	removeWebAuthn: async (event) => {
		const formData = await event.request.formData();
		if (!formData) return fail(400, { error: 'No form data' });

		const form = await superValidate(formData, zod(z.object({ id: z.number() })));
		if (!form.valid) return fail(400, { form });

		const endpoint = `${ALLAUTH_API_URL}/account/authenticators/webauthn`;
		const requestInitOptions: RequestInit = {
			method: 'DELETE',
			body: JSON.stringify({ authenticators: [form.data.id] })
		};

		let response;
		try {
			const res = await event.fetch(endpoint, requestInitOptions);
			response = await res.json();
		} catch {
			return fail(502, { error: 'Could not remove WebAuthn credential' });
		}

		if (response.status !== 200) {
			console.error('Could not remove WebAuthn credential');
			return fail(response.status, { error: 'Could not remove WebAuthn credential' });
		}

		setFlash({ type: 'success', message: m.successfullyRemovedSecurityKey() }, event);
		return { form };
	},
	deletePAT: async (event) => {
		const PATAllowed = !event.locals.user.is_third_party;
		if (!PATAllowed) {
			return fail(403, { error: 'Forbidden' });
		}

		const formData = await event.request.formData();
		if (!formData) return fail(400, { error: 'No form data' });

		const form = await superValidate(formData, zod(z.object({ id: z.string() })));
		if (!form.valid) return fail(400, { form });

		const endpoint = `${BASE_API_URL}/iam/auth-tokens/${form.data.id}/`;
		const requestInitOptions: RequestInit = {
			method: 'DELETE'
		};

		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) {
			console.error('Could not delete PAT');
			return fail(response.status, { form });
		}

		setFlash({ type: 'success', message: m.successfullyDeletedPersonalAccessToken() }, event);
		return message(form, { status: response.status });
	}
};
