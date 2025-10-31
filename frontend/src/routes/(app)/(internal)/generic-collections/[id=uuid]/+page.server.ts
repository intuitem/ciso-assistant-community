import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { superValidate, message } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { modelSchema } from '$lib/utils/schemas';
import type { Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';

// Mapping of URL model types to their many-to-many field names in generic collections
const FIELD_MAP: Record<string, string> = {
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
} as const;

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

	// Create update forms for each many-to-many relationship
	const updateForms = {};
	const updateSchema = modelSchema(URLModel);

	for (const [urlModel, fieldName] of Object.entries(FIELD_MAP)) {
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
		const formData = await event.request.formData();
		const urlModel = formData.get('urlmodel') as string;
		const genericCollectionId = formData.get('genericcollection') as string;

		// Remove genericcollection from the form data before validation
		// since the models don't have this field
		formData.delete('genericcollection');

		// Validate and create the object
		const schema = modelSchema(urlModel);
		const form = await superValidate(formData, zod(schema));

		if (!form.valid) {
			return message(form, { status: 400 });
		}

		// Create the object using the model's endpoint
		const modelInfo = getModelInfo(urlModel);
		const endpoint = modelInfo.endpointUrl
			? `${BASE_API_URL}/${modelInfo.endpointUrl}/`
			: `${BASE_API_URL}/${urlModel}/`;

		const response = await event.fetch(endpoint, {
			method: 'POST',
			body: JSON.stringify(form.data)
		});

		if (!response.ok) {
			const error = await response.json();
			return message(form, { status: response.status, error });
		}

		const createdObject = await response.json();

		// Link the created object to the generic collection
		if (createdObject?.id && genericCollectionId) {
			const fieldName = FIELD_MAP[urlModel];
			if (fieldName) {
				const gcEndpoint = `${BASE_API_URL}/pmbok/generic-collections/${genericCollectionId}/object/`;
				const gcResponse = await event.fetch(gcEndpoint);
				const gcData = await gcResponse.json();

				const updatedField = [...(gcData[fieldName] || []), createdObject.id];

				await event.fetch(`${BASE_API_URL}/pmbok/generic-collections/${genericCollectionId}/`, {
					method: 'PUT',
					body: JSON.stringify({
						...gcData,
						[fieldName]: updatedField
					})
				});
			}
		}

		return message(form, { object: createdObject });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	update: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'generic-collections', action: 'edit' });
	}
};
