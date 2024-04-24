import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { emailSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import { RetryAfterRateLimiter } from 'sveltekit-rate-limiter/server';
import { BASE_API_URL } from '$lib/utils/constants';
import { csrfToken } from '$lib/utils/csrf';
import * as m from '$paraglide/messages';

export const load: PageServerLoad = async (event) => {
	// redirect user if already logged in
	if (event.locals.user) {
		redirect(302, '/');
	}

	const form = await superValidate(event.request, zod(emailSchema));

	await limiter.cookieLimiter?.preflight(event);

	return { form };
};

const limiter = new RetryAfterRateLimiter({
	// A rate is defined as [number, unit]
	rates: {
		IP: [10, 'h'], // IP address limiter
		IPUA: [5, 'm'] // IP + User Agent limiter
	}
});

export const actions: Actions = {
	default: async (event) => {
		const form = await superValidate(event.request, zod(emailSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const email = form.data.email;

		const status = await limiter.check(event);

		if (status.limited) {
			setFlash(
				{
					type: 'error',
					message: m.waitBeforeRequestingResetLink({ timing: status.retryAfter.toString() })
				},
				event
			);
			redirect(302, '/login');
		}

		const endpoint = `${BASE_API_URL}/iam/password-reset/`;

		const requestInitOptions: RequestInit = {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken
			},
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.log(response);
			if (response.error) {
				setFlash({ type: 'error', message: response.error }, event);
			}
			redirect(302, '/login');
		}

		setFlash(
			{
				type: 'success',
				message: m.resetLinkSent({ email: email })
			},
			event
		);

		redirect(302, '/login');
	}
};
