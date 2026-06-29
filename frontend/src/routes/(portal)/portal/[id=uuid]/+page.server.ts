import { defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelSelectFields } from '$lib/utils/crud';
import { formatSelectFieldData } from '$lib/utils/load';
import { modelSchema } from '$lib/utils/schemas';
import { URL_MODEL, type ModelInfo } from '$lib/utils/types';
import { type Actions, error, fail } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

async function buildCreateForm(urlModel: string, fetch: typeof globalThis.fetch) {
	const createForm = await superValidate(zod(modelSchema(urlModel)));
	const model: ModelInfo = getModelInfo(urlModel);
	const selectOptions: Record<string, any> = {};
	for (const selectField of urlParamModelSelectFields(urlModel)) {
		if (selectField.detail) continue;
		const url = `${BASE_API_URL}/${model.endpointUrl ?? urlModel}/${selectField.field}/`;
		const response = await fetch(url);
		if (response.ok) {
			selectOptions[selectField.field] = formatSelectFieldData(await response.json(), selectField);
		}
	}
	model.selectOptions = selectOptions;
	return { createForm, model };
}

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${BASE_API_URL}/portals/${params.id}/content/`);
	if (!res.ok) error(404, 'Portal not found');
	const portal = await res.json();

	const createModels = [
		...new Set(
			(portal.sections ?? [])
				.flatMap((s: any) => s.items ?? [])
				.filter((i: any) => i.kind === 'create' && i.target?.model)
				.map((i: any) => i.target.model as string)
		)
	] as string[];

	const createForms: Record<string, any> = {};
	for (const urlModel of createModels) {
		createForms[urlModel] = await buildCreateForm(urlModel, fetch);
	}

	// The assessment-launch modal picks the domain via FolderTreeSelect, which fetches its
	// own org tree (and the personal "My space" option) client-side — no data needed here.
	return { portal, createForms };
};

export const actions: Actions = {
	create: async (event) => {
		const urlModel = event.url.searchParams.get('model');
		if (!urlModel || !URL_MODEL.includes(urlModel as (typeof URL_MODEL)[number])) {
			return fail(400, { error: 'invalid model' });
		}
		return defaultWriteFormAction({ event, urlModel, action: 'create', doRedirect: false });
	},
	launchAssessment: async ({ params, request, fetch }) => {
		const data = await request.formData();
		const item = data.get('item');
		const folder = data.get('folder') || undefined;
		const name = data.get('name') || undefined;
		const res = await fetch(`${BASE_API_URL}/portals/${params.id}/launch-assessment/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ item, folder, name })
		});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		const { redirect } = await res.json();
		return { redirect };
	}
};
