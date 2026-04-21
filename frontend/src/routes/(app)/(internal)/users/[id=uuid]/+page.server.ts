import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import { loadDetail } from '$lib/utils/load';
import { ServiceAccountKeyCreateSchema } from '$lib/utils/schemas';
import { type Actions, fail } from '@sveltejs/kit';
import { message, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const model = getModelInfo('users');
	return loadDetail({ event, model, id: event.params.id });
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	create: async (event) => {
		const form = await superValidate(event.request, zod(ServiceAccountKeyCreateSchema));
		if (!form.valid) return fail(400, { form });

		const { service_account: _, ...payload } = form.data;
		const res = await event.fetch(`${BASE_API_URL}/iam/service-accounts/${event.params.id}/keys/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			const response = await res.json();
			Object.entries(response).forEach(([key, value]) => {
				(form.errors as Record<string, string[]>)[key] = [String(value)];
			});
			return fail(res.status, { form });
		}

		const obj = await res.json();
		return message(form, { object: obj });
	}
};
