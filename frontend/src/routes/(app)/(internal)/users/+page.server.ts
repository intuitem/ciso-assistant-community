import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelSelectFields } from '$lib/utils/crud';
import { safeTranslate } from '$lib/utils/i18n';
import { modelSchema, ServiceAccountCreateSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import { m } from '$paraglide/messages';
import { type Actions } from '@sveltejs/kit';
import { fail, superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';
import { setFlash } from 'sveltekit-flash-message/server';

const URL_MODEL = 'users';

function buildTableSource(model: string) {
	const fields = listViewFields[model as keyof typeof listViewFields] as {
		head: string[];
		body: string[];
	};
	const headData: Record<string, string> = fields.body.reduce(
		(obj: Record<string, string>, key: string, index: number) => {
			obj[key] = fields.head[index];
			return obj;
		},
		{}
	);
	return { head: headData, body: [], meta: [] };
}

export const load: PageServerLoad = async ({ fetch, locals }) => {
	const deleteForm = await superValidate(zod(z.object({ id: z.string().uuid() })));
	const createSchema = modelSchema(URL_MODEL);
	const createForm = await superValidate(zod(createSchema));
	const model = getModelInfo(URL_MODEL);
	const selectFields = urlParamModelSelectFields(URL_MODEL);

	const selectOptions: Record<string, any> = {};
	for (const selectField of selectFields) {
		if (selectField.detail) continue;
		const url = `${BASE_API_URL}/${URL_MODEL}/${selectField.field}/`;
		const response = await fetch(url);
		if (response.ok) {
			selectOptions[selectField.field] = await response
				.json()
				.then((data: any) =>
					Object.entries(data).map(([key, value]) => ({ label: value, value: key }))
				);
		}
	}
	model['selectOptions'] = selectOptions;

	const serviceAccountsEnabled = locals.featureflags?.service_accounts ?? false;
	const createSAForm = serviceAccountsEnabled
		? await superValidate(zod(ServiceAccountCreateSchema))
		: null;

	return {
		createForm,
		deleteForm,
		model,
		URLModel: URL_MODEL,
		table: buildTableSource('users'),
		saTable: serviceAccountsEnabled ? buildTableSource('service-accounts') : null,
		createSAForm
	};
};

export const actions: Actions = {
	// ── Users ──────────────────────────────────────────────────────────────
	create: async (event) => {
		return defaultWriteFormAction({ event, urlModel: URL_MODEL, action: 'create' });
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: URL_MODEL });
	},

	// ── Service accounts ───────────────────────────────────────────────────
	createSA: async (event) => {
		const form = await superValidate(event.request, zod(ServiceAccountCreateSchema));
		if (!form.valid) return fail(400, { form });

		const res = await event.fetch(`${BASE_API_URL}/iam/service-accounts/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(form.data)
		});

		if (!res.ok) {
			try {
				const response = await res.json();
				if (response.error) {
					setFlash({ type: 'error', message: safeTranslate(response.error) }, event);
					return fail(res.status, { form });
				}
				Object.entries(response).forEach(([key, value]) => {
					const msg = Array.isArray(value)
						? value.map((v: string) => safeTranslate(v)).join(', ')
						: safeTranslate(value as string);
					(form.errors as Record<string, string[]>)[key] = [msg];
				});
			} catch (e) {
				console.error('Failed to parse error response', e);
			}
			return fail(res.status, { form });
		}

		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({ object: m.serviceAccount().toLowerCase() })
			},
			event
		);
		return { form };
	},

	deleteSA: async (event) => {
		const form = await superValidate(event.request, zod(z.object({ id: z.string().uuid() })));
		if (!form.valid) return fail(400, { form });

		const res = await event.fetch(`${BASE_API_URL}/iam/service-accounts/${form.data.id}/`, {
			method: 'DELETE'
		});

		if (!res.ok) {
			let msg = m.anErrorOccurred();
			try {
				const response = await res.json();
				msg = safeTranslate(response.error ?? response.detail ?? 'anErrorOccurred');
			} catch (e) {
				console.error('Failed to parse error response', e);
			}
			setFlash({ type: 'error', message: msg }, event);
			return fail(res.status, { form });
		}

		setFlash(
			{
				type: 'success',
				message: m.successfullyDeletedObject({ object: m.serviceAccount().toLowerCase() })
			},
			event
		);
		return { form };
	}
};
