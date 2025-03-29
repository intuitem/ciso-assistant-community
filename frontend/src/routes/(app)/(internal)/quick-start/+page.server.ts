import { defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { quickStartSchema } from '$lib/utils/schemas';
import { type Actions } from '@sveltejs/kit';
import { fail, message, setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';

export const actions: Actions = {
	create: async (event) => {
		const formData = await event.request.formData();
		if (!formData) {
			return fail(400, { form: null });
		}

		const form = await superValidate(formData, zod(quickStartSchema));

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const endpoint = `${BASE_API_URL}/quick-start/`;
		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response = await res.json();
			console.error(response);
			if (response.errors) {
				response.errors.forEach((error) => {
					setError(form, error.param, error.code);
				});
				return fail(res.status, { form });
			}
		}

		const response = await res.json();

		return message(form, {
			redirect: `/compliance-assessments/${response.complianceassessment.id}`
		});
	}
};
