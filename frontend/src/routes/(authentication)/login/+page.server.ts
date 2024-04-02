import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { LoginRequestBody } from '$lib/utils/types';
import { BASE_API_URL } from '$lib/utils/constants';
import { csrfToken } from '$lib/utils/csrf';
import { loginSchema } from '$lib/utils/schemas';
import { setError, superValidate } from 'sveltekit-superforms/server';
import { base } from '$app/paths';

export const load: PageServerLoad = async ({ request, locals }) => {
	// redirect user if already logged in
	if (locals.user) {
		redirect(301, `${base}/analytics`);
	}

	const form = await superValidate(request, loginSchema);

	return { form };
};

export const actions: Actions = {
	default: async ({ request, url, fetch, cookies }) => {
		const form = await superValidate(request, loginSchema);
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
			console.log(response.non_field_errors);
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			return { form };
		}

		if (res.headers.has('Set-Cookie')) {
			const splitted = Object.fromEntries(res.headers)
				['set-cookie'].split(' ')
				.filter((string) => string.indexOf('=') >= 0 && string.split('=')[0] === 'sessionid')
				.map((string) => string.split('=')[1]);

			if (splitted.length < 1) {
				throw fail(500, {
					message:
						"Failed to create a session, the API returned cookies the 'sessionid' cookie is missing !"
				});
			}

			const sessionid = splitted[0];
			cookies.set('sessionid', sessionid, {
				httpOnly: true,
				sameSite: 'lax',
				path: '/',
				secure: true
			});

			const csrftoken = cookies.get('csrftoken');
			if (csrftoken) {
				cookies.set('csrftoken', csrftoken, {
					// Setting httpOnly to true for the CSRF token offers no additional security.
					// https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
					httpOnly: false,
					sameSite: 'lax',
					path: '/',
					secure: true
				});
			}
		}
		redirect(302, url.searchParams.get('next') || `${base}/analytics`);
	}
};
