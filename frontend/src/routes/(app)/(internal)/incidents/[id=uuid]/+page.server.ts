import { getModelInfo } from '$lib/utils/crud';

import { type Actions } from '@sveltejs/kit';
import {
	nestedDeleteFormAction,
	defaultWriteFormAction,
	nestedWriteFormAction
} from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('incidents');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	const evidenceModel = getModelInfo('evidences');
	const evidenceCreateSchema = modelSchema('evidences');
	const evidenceCreateForm = await superValidate(
		{ folder: data.data.folder.id },
		zod(evidenceCreateSchema),
		{ errors: false }
	);

	async function fetchJson(url: string) {
		const res = await fetch(url);
		if (!res.ok) {
			console.error(`Failed to fetch data from ${url}: ${res.statusText}`);
			return null;
		}
		return res.json();
	}

	const evidenceSelectOptions: Record<string, any> = {};
	if (evidenceModel.selectFields) {
		await Promise.all(
			evidenceModel.selectFields.map(async (selectField) => {
				const url = `${BASE_API_URL}/evidences/${selectField.field}/`;
				const data = await fetchJson(url);
				if (data) {
					evidenceSelectOptions[selectField.field] = Object.entries(data).map(([key, value]) => ({
						label: value,
						value: selectField.valueType === 'number' ? parseInt(key) : key
					}));
				}
			})
		);
	}
	evidenceModel.selectOptions = evidenceSelectOptions;

	data['evidenceModel'] = evidenceModel;
	data['evidenceCreateForm'] = evidenceCreateForm;

	return data;
};

export const actions: Actions = {
	create: async (event) => {
		const redirectToWrittenObject = Boolean(event.params.model === 'perimeters');
		return defaultWriteFormAction({
			event,
			urlModel: 'timeline-entries',
			action: 'create',
			redirectToWrittenObject
		});
	},
	delete: async (event) => {
		console.log('delete');
		return nestedDeleteFormAction({ event });
	},
	createEvidence: async (event) => {
		const result = await nestedWriteFormAction({ event, action: 'create' });
		if (result.form) return { form: result.form, newEvidence: result.form.message.object.id };
		else return result;
	}
};
