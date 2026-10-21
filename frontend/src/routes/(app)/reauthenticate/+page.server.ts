import { ALLAUTH_API_URL } from '$lib/utils/constants';
import { getSecureRedirect } from '$lib/utils/helpers';
import { reauthenticateSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { fail, redirect } from '@sveltejs/kit';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const form = await superValidate(zod(reauthenticateSchema));
	const method = url.searchParams.get('method') === 'code' ? 'code' : 'password';
	return { form, method, title: m.password() };
};

export const actions: Actions = {
	default: async (event) => {
		const form = await superValidate(event.request, zod(reauthenticateSchema));
		if (!form.valid) return fail(400, { form });

		const field = event.url.searchParams.get('method') === 'code' ? 'code' : 'password';
		const endpoint = field === 'code' ? 'auth/2fa/reauthenticate' : 'auth/reauthenticate';

		const res = await event
			.fetch(`${ALLAUTH_API_URL}/${endpoint}`, {
				method: 'POST',
				body: JSON.stringify({ [field]: form.data[field] })
			})
			.then((res) => res.json());

		if (res.status !== 200) {
			res.errors?.forEach((error: { message: string }) => {
				setError(form, field, error.message);
			});
			return fail(res.status, { form });
		}

		redirect(302, getSecureRedirect(event.url.searchParams.get('next')) || '/');
	}
};
