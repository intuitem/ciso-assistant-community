import { ALLAUTH_API_URL } from '$lib/utils/constants';
import { getSecureRedirect } from '$lib/utils/helpers';
import { reauthenticateSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { fail, redirect } from '@sveltejs/kit';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { Actions, PageServerLoad } from './$types';

const ENDPOINTS = {
	password: 'auth/reauthenticate',
	code: 'auth/2fa/reauthenticate',
	webauthn: 'auth/webauthn/reauthenticate'
};

function getMethod(url: URL): keyof typeof ENDPOINTS {
	const method = url.searchParams.get('method');
	return method === 'code' || method === 'webauthn' ? method : 'password';
}

export const load: PageServerLoad = async ({ url, fetch }) => {
	const form = await superValidate(zod(reauthenticateSchema));
	const method = getMethod(url);
	let requestOptions = null;
	if (method === 'webauthn') {
		const res = await fetch(`${ALLAUTH_API_URL}/${ENDPOINTS.webauthn}`).then((res) => res.json());
		requestOptions = res.data?.request_options ?? null;
	}
	return { form, method, requestOptions, title: m.password() };
};

export const actions: Actions = {
	default: async (event) => {
		const form = await superValidate(event.request, zod(reauthenticateSchema));
		if (!form.valid) return fail(400, { form });

		const method = getMethod(event.url);
		const field = method === 'webauthn' ? 'credential' : method;

		let value: unknown = form.data[field];
		if (method === 'webauthn') {
			try {
				value = JSON.parse(form.data.credential ?? '');
			} catch {
				setError(form, field, m.webAuthnError());
				return fail(400, { form });
			}
		}

		const res = await event
			.fetch(`${ALLAUTH_API_URL}/${ENDPOINTS[method]}`, {
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
