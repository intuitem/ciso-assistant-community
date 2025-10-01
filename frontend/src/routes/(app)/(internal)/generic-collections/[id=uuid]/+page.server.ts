import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { modelSchema } from '$lib/utils/schemas';
import type { Actions } from '@sveltejs/kit';
import {
	nestedDeleteFormAction,
	nestedWriteFormAction,
	defaultWriteFormAction
} from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';

export const load: PageServerLoad = async (event) => {
	const URLModel = 'generic-collections';
	const modelInfo = getModelInfo(URLModel);

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	// Fetch the full object data for updates
	const objectEndpoint = `${BASE_API_URL}/${modelInfo.endpointUrl || URLModel}/${event.params.id}/object/`;
	const objectResponse = await event.fetch(objectEndpoint);
	const object = await objectResponse.json();

	// Mapping of field names for update forms
	const fieldMap: Record<string, string> = {
		'compliance-assessments': 'compliance_assessments',
		'risk-assessments': 'risk_assessments',
		'quantitative-risk-studies': 'crq_studies',
		'ebios-rm': 'ebios_studies',
		'entity-assessments': 'entity_assessments',
		'findings-assessments': 'findings_assessments',
		evidences: 'documents',
		'security-exceptions': 'security_exceptions',
		policies: 'policies',
		'generic-collections': 'dependencies'
	};

	// Create update forms for each many-to-many relationship
	const updateForms = {};
	const updateSchema = modelSchema(URLModel);

	for (const [urlModel, fieldName] of Object.entries(fieldMap)) {
		// Include all required fields from object to pass validation
		const formData = {
			name: object.name,
			description: object.description,
			folder: object.folder,
			ref_id: object.ref_id,
			[fieldName]: object[fieldName] || []
		};
		updateForms[fieldName] = await superValidate(formData, zod(updateSchema), { errors: false });
	}

	return {
		...data,
		updateForms,
		object
	};
};

export const actions: Actions = {
	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create', redirectToWrittenObject: false });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	update: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'generic-collections', action: 'edit' });
	}
};
