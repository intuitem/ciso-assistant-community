import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { getSecureRedirect } from '$lib/utils/helpers';
import { safeTranslate } from '$lib/utils/i18n';
import { ServiceAccountKeyUpdateSchema } from '$lib/utils/schemas';
import { m } from '$paraglide/messages';
import { error, fail, redirect, type Actions, type NumericRange } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const URLModel = 'service-account-keys';
	const model = getModelInfo(URLModel);

	const res = await fetch(`${BASE_API_URL}/iam/service-account-keys/${params.id}/`);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, 'Not found');
	}
	const object = await res.json();
	const form = await superValidate(object, zod(ServiceAccountKeyUpdateSchema));

	return { form, model, object, title: m.edit() };
};

export const actions: Actions = {
	default: async (event) => {
		const form = await superValidate(event.request, zod(ServiceAccountKeyUpdateSchema));

		if (!form.valid) {
			return fail(400, { form });
		}

		const res = await event.fetch(`${BASE_API_URL}/iam/service-account-keys/${event.params.id}/`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(form.data)
		});

		if (!res.ok) {
			const response = await res.json();
			if (response.error) {
				setFlash({ type: 'error', message: safeTranslate(response.error) }, event);
				return fail(res.status, { form });
			}
			Object.entries(response).forEach(([key, value]) => {
				const msg = Array.isArray(value)
					? value.map(safeTranslate).join(', ')
					: safeTranslate(value as string);
				setError(form, key, msg);
			});
			return fail(res.status, { form });
		}

		setFlash(
			{ type: 'success', message: m.successfullyUpdatedObject({ object: m.serviceAccountKey() }) },
			event
		);
		redirect(302, getSecureRedirect(event.url.searchParams.get('next')) ?? `/users`);
	}
};
