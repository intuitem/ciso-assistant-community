import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { getSecureRedirect } from '$lib/utils/helpers';
import { safeTranslate } from '$lib/utils/i18n';
import { UserEditSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const URLModel = 'users';
	const model = getModelInfo(URLModel);
	const objectEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/object/`;
	const readEndpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const [object, readObject] = await Promise.all([
		fetch(objectEndpoint).then((res) => res.json()),
		fetch(readEndpoint).then((res) => res.json())
	]);
	const schema = UserEditSchema;
	const form = await superValidate(object, zod(schema));

	return {
		form,
		model,
		object: { ...object, has_mfa_enabled: readObject.has_mfa_enabled },
		title: m.edit()
	};
};

export const actions: Actions = {
	resetMFA: async (event) => {
		const endpoint = `${BASE_API_URL}/iam/reset-mfa/`;
		const res = await event.fetch(endpoint, {
			method: 'POST',
			body: JSON.stringify({ user: event.params.id })
		});

		if (!res.ok) {
			const response = await res.json();
			setFlash(
				{ type: 'error', message: safeTranslate(response.error ?? 'mfaResetFailed') },
				event
			);
			return fail(res.status);
		}

		setFlash({ type: 'success', message: m.mfaSuccessfullyReset() }, event);
		return {};
	},
	updateUser: async (event) => {
		const schema = UserEditSchema;
		const endpoint = `${BASE_API_URL}/users/${event.params.id}/`;
		const form = await superValidate(event.request, zod(schema));

		if (!form.valid) {
			console.log(form.errors);
			return fail(400, { form: form });
		}

		const requestInitOptions: RequestInit = {
			method: 'PUT',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error('server response:', response);
			if (response.error) {
				setFlash({ type: 'error', message: safeTranslate(response.error) }, event);
				return fail(403, { form: form });
			}
			if (response.non_field_errors) {
				setError(form, 'non_field_errors', response.non_field_errors);
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, safeTranslate(value));
			});
			return fail(400, { form: form });
		}
		setFlash(
			{ type: 'success', message: m.successfullyUpdatedUser({ email: form.data.email }) },
			event
		);
		redirect(
			302,
			getSecureRedirect(event.url.searchParams.get('next')) ?? `/users/${event.params.id}`
		);
	}
};
