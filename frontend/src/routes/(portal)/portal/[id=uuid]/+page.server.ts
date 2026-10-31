import { defaultWriteFormAction } from '#lib/utils/actions.js';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo, URL_MODEL_MAP, urlParamModelSelectFields } from '#lib/utils/crud.js';
import { hasPermissionAnywhere } from '#lib/utils/access-control.js';
import { canUseTile } from '#lib/utils/portalTileAccess.js';
import { formatSelectFieldData } from '#lib/utils/load.js';
import { modelSchema } from '#lib/utils/schemas.js';
import { URL_MODEL, type ModelInfo } from '#lib/utils/types.js';
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

export const load: PageServerLoad = async ({ params, fetch, locals }) => {
	const res = await fetch(`${BASE_API_URL}/portals/${params.id}/content/`);
	if (!res.ok) error(404, 'Portal not found');
	const portal = await res.json();

	// Hide tiles that would only error for this viewer (no permission, unreadable document).
	// UX only: the API still enforces every action behind a tile.
	const user = await locals.getUser();
	const items = (portal.sections ?? []).flatMap((s: any) => s.items ?? []);
	const hasDocumentTile = items.some(
		(i: any) => i.target?.model === 'documents' && i.target?.document
	);
	const catalogRes = hasDocumentTile
		? await fetch(`${BASE_API_URL}/document-containers/catalog/`)
		: null;
	const access = {
		has: (codename: string) => hasPermissionAnywhere(user, codename),
		modelName: (urlModel: string) => URL_MODEL_MAP[urlModel]?.name,
		readableDocuments: new Set<string>(
			catalogRes?.ok ? (await catalogRes.json()).map((c: any) => c.id) : []
		)
	};
	portal.sections = (portal.sections ?? [])
		.map((s: any) => ({ ...s, items: (s.items ?? []).filter((i: any) => canUseTile(i, access)) }))
		.filter((s: any) => s.items.length);

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

// The tile launch banner prints this verbatim, so hand it the backend's message
// rather than the JSON envelope around it.
const readError = async (res: Response) => {
	const body = await res.text();
	try {
		const parsed = JSON.parse(body);
		return parsed?.detail ?? parsed?.error ?? body;
	} catch {
		return body;
	}
};

export const actions: Actions = {
	create: async (event) => {
		const urlModel = event.url.searchParams.get('model');
		if (!urlModel || !URL_MODEL.includes(urlModel as (typeof URL_MODEL)[number])) {
			return fail(400, { error: 'invalid model' });
		}
		return defaultWriteFormAction({ event, urlModel, action: 'create', doRedirect: false });
	},
	launchQuickForm: async ({ params, request, fetch }) => {
		const data = await request.formData();
		const res = await fetch(`${BASE_API_URL}/portals/${params.id}/launch-quick-form/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				item: data.get('item'),
				folder: data.get('folder') || undefined,
				name: data.get('name') || undefined
			})
		});
		if (!res.ok) return fail(res.status, { error: await readError(res) });
		// resumed/ref_id drive the "we handed you your draft back" banner; dropping them
		// here made that banner unreachable from a tile.
		const { redirect, resumed, ref_id } = await res.json();
		return { redirect, resumed, ref_id };
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
		if (!res.ok) return fail(res.status, { error: await readError(res) });
		const { redirect } = await res.json();
		return { redirect };
	}
};
