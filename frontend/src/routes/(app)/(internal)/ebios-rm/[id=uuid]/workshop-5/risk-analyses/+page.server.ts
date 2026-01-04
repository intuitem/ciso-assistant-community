import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { listViewFields } from '$lib/utils/table';
import type { ModelInfo, urlModel } from '$lib/utils/types';
import { type TableSource } from '@skeletonlabs/skeleton-svelte';
import { type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch, url }) => {
	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(zod(schema));
	const URLModel = 'risk-assessments';
	const createSchema = modelSchema(URLModel);
	const ebiosMatrixRes = await fetch(`${BASE_API_URL}/ebios-rm/studies/${params.id}/risk-matrix/`);
	const risk_matrix_id = await ebiosMatrixRes.json().then((res) => res.id);
	const initialData = {
		ebios_rm_study: params.id,
		risk_matrix: risk_matrix_id
	};
	const createForm = await superValidate(initialData, zod(createSchema), { errors: false });
	const model: ModelInfo = getModelInfo(URLModel);
	const selectFields = model.selectFields;

	const selectOptions: Record<string, any> = {};

	if (selectFields) {
		for (const selectField of selectFields) {
			const url = `${BASE_API_URL}/${URLModel}/${
				selectField.detail ? params.id + '/' : ''
			}${selectField.field}/`;
			const response = await fetch(url);
			if (response.ok) {
				selectOptions[selectField.field] = await response.json().then((data) =>
					Object.entries(data).map(([key, value]) => ({
						label: value,
						value: key
					}))
				);
			} else {
				console.error(`Failed to fetch data for ${selectField.field}: ${response.statusText}`);
			}
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

	// Check if there's already a risk assessment for this EBIOS RM study
	const riskAssessmentsRes = await fetch(
		`${BASE_API_URL}/risk-assessments/?ebios_rm_study=${params.id}`
	);
	let lastRiskAssessment = null;
	let riskAssessmentToSync = null;

	if (riskAssessmentsRes.ok) {
		const riskAssessments = await riskAssessmentsRes.json();
		if (riskAssessments.results && riskAssessments.results.length > 0) {
			// Get the most recent one (assuming they're ordered by created_at desc)
			lastRiskAssessment = riskAssessments.results[0];
		}
	}

	// Check if there's a specific risk assessment to sync from URL parameter
	const syncId = url.searchParams.get('sync');
	if (syncId) {
		const syncRiskAssessmentRes = await fetch(`${BASE_API_URL}/risk-assessments/${syncId}/`);
		if (syncRiskAssessmentRes.ok) {
			riskAssessmentToSync = await syncRiskAssessmentRes.json();
		}
	}

	return {
		createForm,
		deleteForm,
		model,
		URLModel,
		table,
		lastRiskAssessment,
		riskAssessmentToSync,
		title: m.riskAnalyses(),
		modelVerboseName: m.ebiosRmRiskAnalysesSubtitle()
	};
};

export const actions: Actions = {
	create: async (event) => {
		// const redirectToWrittenObject = Boolean(event.params.model === 'entity-assessments');
		return defaultWriteFormAction({
			event,
			urlModel: 'risk-assessments',
			action: 'create'
			// redirectToWrittenObject: redirectToWrittenObject
		});
	},
	delete: async (event) => {
		return defaultDeleteFormAction({ event, urlModel: 'risk-assessments' });
	},
	sync: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const riskAssessmentId = formData.get('risk_assessment_id');

		const response = await fetch(
			`${BASE_API_URL}/risk-assessments/${riskAssessmentId}/sync_from_ebios_rm/`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			}
		);

		if (response.ok) {
			const result = await response.json();
			return {
				success: true,
				message: `Synchronization complete: ${result.updated} updated, ${result.created} created, ${result.archived} archived`,
				result
			};
		} else {
			const error = await response.json();
			return {
				success: false,
				message: error.error || 'Synchronization failed'
			};
		}
	}
};
