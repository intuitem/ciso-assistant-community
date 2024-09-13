import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { fail, setError, superValidate } from 'sveltekit-superforms';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';
import { zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import * as m from '$paraglide/messages';
import { z } from 'zod';
import { safeTranslate } from '$lib/utils/i18n';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const [compliance_assessment, tableMode] = await Promise.all(
		[endpoint, `${endpoint}requirements_list/`].map((endpoint) =>
			fetch(endpoint).then((res) => res.json())
		)
	);

	const evidenceModel = getModelInfo('evidences');
	const evidenceCreateSchema = modelSchema('evidences');
	const requirement_assessments = await Promise.all(
		tableMode.requirement_assessments.map(async (requirementAssessment) => {
			const evidenceInitialData = {
				requirement_assessments: [requirementAssessment.id],
				folder: requirementAssessment.folder.id
			};
			const evidenceCreateForm = await superValidate(
				evidenceInitialData,
				zod(evidenceCreateSchema),
				{
					errors: false
				}
			);
			const observationBuffer = requirementAssessment.observation;
			return {
				...requirementAssessment,
				evidenceCreateForm,
				observationBuffer
			};
		})
	);
	const requirements = tableMode.requirements;

	const schema = z.object({ id: z.string().uuid() });
	const deleteForm = await superValidate(zod(schema));

	return {
		URLModel,
		compliance_assessment,
		requirement_assessments,
		requirements,
		evidenceModel,
		deleteForm
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	updateRequirementAssessment: async (event) => {
		const data = await event.request.json();
		const value: { id: string; result: string } = data;
		const URLModel = 'requirement-assessments';
		const endpoint = `${BASE_API_URL}/${URLModel}/${value.id}/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(value)
		};

		const res = await event.fetch(endpoint, requestInitOptions);
		return { status: res.status, body: await res.json() };
	},
	createEvidence: async (event) => {
		const formData = await event.request.formData();

		if (!formData) {
			return fail(400, { form: null });
		}

		const schema = modelSchema('evidences');
		const form = await superValidate(formData, zod(schema));

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		const endpoint = `${BASE_API_URL}/evidences/`;

		const model = getModelInfo('evidences');

		const fileFields: Record<string, File> = Object.fromEntries(
			Object.entries(form.data).filter(([key]) => model.fileFields?.includes(key) ?? false)
		);

		Object.keys(fileFields).forEach((key) => {
			form.data[key] = undefined;
		});

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};

		const res = await event.fetch(endpoint, requestInitOptions);

		if (!res.ok) {
			const response: Record<string, any> = await res.json();
			console.error(response);
			if (response.warning) {
				setFlash({ type: 'warning', message: response.warning }, event);
				return { createForm: form };
			}
			if (response.error) {
				setFlash({ type: 'error', message: response.error }, event);
				return { createForm: form };
			}
			Object.entries(response).forEach(([key, value]) => {
				setError(form, key, value);
			});
			return fail(400, { form: form });
		}

		const createdEvidence = await res.json();

		if (fileFields) {
			for (const [, file] of Object.entries(fileFields)) {
				if (!file) continue;
				if (file.size <= 0) continue;
				const fileUploadEndpoint = `${BASE_API_URL}/${'evidences'}/${createdEvidence.id}/upload/`;
				const fileUploadRequestInitOptions: RequestInit = {
					headers: {
						'Content-Disposition': `attachment; filename=${encodeURIComponent(file.name)}`
					},
					method: 'POST',
					body: file
				};
				const fileUploadRes = await event.fetch(fileUploadEndpoint, fileUploadRequestInitOptions);
				if (!fileUploadRes.ok) {
					const response = await fileUploadRes.json();
					console.error(response);
					if (response.non_field_errors) {
						setError(form, 'non_field_errors', response.non_field_errors);
					}
					return fail(400, { form: form });
				}
			}
		}

		setFlash(
			{
				type: 'success',
				message: m.successfullyCreatedObject({
					object: m.evidence().toLowerCase()
				})
			},
			event
		);
		return { createForm: form, createdEvidence };
	},
	deleteEvidence: async (event) => {
		const formData = await event.request.formData();
		const schema = z.object({ id: z.string().uuid() });
		const deleteForm = await superValidate(formData, zod(schema));

		const id = deleteForm.data.id;
		const endpoint = `${BASE_API_URL}/evidences/${id}/`;

		if (!deleteForm.valid) {
			console.log(deleteForm.errors);
			return fail(400, { form: deleteForm });
		}

		if (formData.has('delete')) {
			const requestInitOptions: RequestInit = {
				method: 'DELETE'
			};
			const res = await event.fetch(endpoint, requestInitOptions);
			if (!res.ok) {
				const response = await res.json();
				console.log(response);
				if (response.error) {
					setFlash({ type: 'error', message: safeTranslate(response.error) }, event);
					return fail(403, { form: deleteForm });
				}
				if (response.non_field_errors) {
					setError(deleteForm, 'non_field_errors', response.non_field_errors);
				}
				return fail(400, { form: deleteForm });
			}
			const model: string = urlParamModelVerboseName(event.params.model!);
			setFlash(
				{
					type: 'success',
					message: m.successfullyDeletedObject({
						object: safeTranslate(model).toLowerCase()
					})
				},
				event
			);
		}
		return { deleteForm };
	}
};
