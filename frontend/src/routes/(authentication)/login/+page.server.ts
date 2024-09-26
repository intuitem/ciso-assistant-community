import { getSecureRedirect } from '$lib/utils/helpers';

import { fail, redirect, type Actions } from '@sveltejs/kit';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import type { LoginRequestBody } from '$lib/utils/types';
import { BASE_API_URL } from '$lib/utils/constants';
import { csrfToken } from '$lib/utils/csrf';
import { loginSchema } from '$lib/utils/schemas';
import { setError, superValidate } from 'sveltekit-superforms';
export const load: PageServerLoad = async ({ fetch, request, locals }) => {
	// redirect user if already logged in
	if (locals.user) {
		redirect(302, '/analytics');
	}

	const form = await superValidate(request, zod(loginSchema));

	const SSOInfo = await fetch(`${BASE_API_URL}/settings/sso/info/`).then((res) => res.json());

	return { form, SSOInfo };
};

export const actions: Actions = {
	default: async ({ request, url, fetch, cookies }) => {
		const form = await superValidate(request, zod(loginSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const username = form.data.username;
		const password = form.data.password;

		const login: LoginRequestBody = {
			username,
			password
		};

		const endpoint = `${BASE_API_URL}/iam/login/`;

		const requestInitOptions: RequestInit = {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken
			},
			body: JSON.stringify(login)
		};

		const res = await fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error(response);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			return { form };
		}

		const data = await res.json();

		cookies.set('token', data.token, {
			httpOnly: true,
			sameSite: 'lax',
			path: '/',
			secure: true
		});

		redirect(302, getSecureRedirect(url.searchParams.get('next')) || '/analytics');
	}
};
