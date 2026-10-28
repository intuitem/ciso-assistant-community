import { ALLAUTH_API_URL } from '#lib/utils/constants.js';
import { getSecureRedirect } from '#lib/utils/helpers.js';
import { reauthenticateSchema } from '#lib/utils/schemas.js';
import { m } from '#paraglide/messages.js';
import { fail, redirect } from '@sveltejs/kit';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { Actions, PageServerLoad } from './$types';

const MFA_TYPES = ['webauthn', 'totp', 'recovery_codes'];

export const load: PageServerLoad = async ({ url, fetch }) => {
	const mfaTypes =
		url.searchParams.get('method') === 'mfa'
			? MFA_TYPES.filter((type) => url.searchParams.get('types')?.split(',').includes(type))
			: [];
	const form = await superValidate(
		{ mode: (mfaTypes[0] ?? 'password') as 'webauthn' | 'totp' | 'recovery_codes' | 'password' },
		zod(reauthenticateSchema),
		{ errors: false }
	);
	let requestOptions = null;
	if (mfaTypes.includes('webauthn')) {
		const res = await fetch(`${ALLAUTH_API_URL}/auth/webauthn/reauthenticate`).then((res) =>
			res.json()
		);
		requestOptions = res.data?.request_options ?? null;
	}
	return { form, mfaTypes, requestOptions, title: m.password() };
};

export const actions: Actions = {
	default: async (event) => {
		const form = await superValidate(event.request, zod(reauthenticateSchema));
		if (!form.valid) return fail(400, { form });

		const field = form.data.credential ? 'credential' : form.data.code ? 'code' : 'password';
		const endpoint = {
			credential: 'auth/webauthn/reauthenticate',
			code: 'auth/2fa/reauthenticate',
			password: 'auth/reauthenticate'
		}[field];

		let value: unknown = form.data[field];
		if (field === 'credential') {
			try {
				value = JSON.parse(form.data.credential ?? '');
			} catch {
				setError(form, field, m.webAuthnError());
				return fail(400, { form });
			}
		}

		const res = await event
			.fetch(`${ALLAUTH_API_URL}/${endpoint}`, {
				method: 'POST',
				body: JSON.stringify({ [field]: value })
			})
			.then((res) => res.json());

		if (res.status !== 200) {
			const messages = res.errors?.map((error: { message: string }) => error.message) ?? [];
			if (messages.length === 0) {
				messages.push(res.status === 429 ? m.tooManyAttempts() : m.error());
			}
			setError(form, field, messages);
			return fail(res.status, { form });
		}

		redirect(302, getSecureRedirect(event.url.searchParams.get('next')) || '/');
	}
};
