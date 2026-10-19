import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelSelectFields } from '$lib/utils/crud';
import { formatSelectFieldData } from '$lib/utils/load';
import { fetchAllPages } from '$lib/utils/pagination';
import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { ModelInfo, urlModel } from '$lib/utils/types';
import { type TableSource } from '$lib/components/ModelTable/types';
import { type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(zod(schema));
	const URLModel = 'ro-to';
	const createSchema = modelSchema(URLModel);
	const objectEndpoint = `${BASE_API_URL}/ebios-rm/studies/${params.id}/object/`;
	const objectResponse = await fetch(objectEndpoint);
	let object: any = {};
	if (objectResponse.ok) {
		object = await objectResponse.json();
	} else {
		console.error(`Failed to fetch study object: ${objectResponse.statusText}`);
	}
	const initialData = {
		ebios_rm_study: params.id,
		folder: object.folder
	};
	const createForm = await superValidate(initialData, zod(createSchema), { errors: false });
	const model: ModelInfo = getModelInfo(URLModel);
	const selectFields = urlParamModelSelectFields(URLModel);

	const selectOptions: Record<string, any> = {};

	for (const selectField of selectFields) {
		const studyScoped = selectField.detail && selectField.formNestedField === 'ebios_rm_study';
		if (selectField.detail && !studyScoped) continue;
		const url = studyScoped
			? `${BASE_API_URL}/${selectField.endpointUrl}/${params.id}/${selectField.field}/`
			: `${BASE_API_URL}/${model.endpointUrl ?? model.urlModel}/${selectField.field}/`;
		const response = await fetch(url);
		if (response.ok) {
			const responseData = await response.json();
			selectOptions[selectField.field] = formatSelectFieldData(responseData, selectField);
		} else {
			console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
		}
	}

	model['selectOptions'] = selectOptions;

	const headData: Record<string, string> = listViewFields[URLModel as urlModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields[URLModel as urlModel].head[index];
			return obj;
		},
		{}
	);

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	// Data for the risk origins map (M2_09): every couple of the study, plus the
	// pertinence labels of the study's matrix, lowest level first.
	const [couples, ratingKit] = await Promise.all([
		fetchAllPages<any>(fetch, `${BASE_API_URL}/ebios-rm/ro-to/?ebios_rm_study=${params.id}`),
		fetch(`${BASE_API_URL}/ebios-rm/studies/${params.id}/rating-kit/`).then((res) =>
			res.ok ? res.json() : null
		)
	]);

	return {
		couples,
		pertinenceLevels: ratingKit?.ro_to?.pertinence ?? [],
		createForm,
		deleteForm,
		model,
		URLModel,
		table,
		title: m.roToCouples(),
		modelVerboseName: m.ebiosRmRoToSubtitle()
	};
};

export const actions: Actions = {
	create: async (event) => {
		// const redirectToWrittenObject = Boolean(event.params.model === 'entity-assessments');
		return defaultWriteFormAction({
			event,
			urlModel: 'ro-to',
			action: 'create'
			// redirectToWrittenObject: redirectToWrittenObject
		});
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: 'ro-to' });
	}
};
