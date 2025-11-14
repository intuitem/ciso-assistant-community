import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelVerboseName } from '$lib/utils/crud';

import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';

import { fail, type Actions } from '@sveltejs/kit';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { setFlash } from 'sveltekit-flash-message/server';
import { zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import {
	nestedDeleteFormAction,
	nestedWriteFormAction,
	handleErrorResponse,
	defaultWriteFormAction
} from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';

import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

interface SelectableModel {
	backendViewset?: string;
	field: string;
	optionsEndpoint: string;
	updatedObjectName: string;
}

const SELECT_MAP: Record<string, Record<string, SelectableModel>> = {
	'applied-controls': {
		// m.appliedControl() is considered as the updatedObjectName (as evidences is a M2M field of the applied control)
		evidences: {
			field: 'evidences',
			optionsEndpoint: 'evidences',
			updatedObjectName: m.appliedControl()
		},
		'task-templates': {
			backendViewset: 'task-templates',
			field: 'applied_controls',
			optionsEndpoint: 'task-templates',
			updatedObjectName: m.tasks()
		}
	}
};

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo(event.params.model);

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	const objectEndpoint = `${BASE_API_URL}/${modelInfo.endpointUrl || event.params.model}/${event.params.id}/object/`;
	const objectResponse = await event.fetch(objectEndpoint);
	const object = await objectResponse.json();

	const modelsToSelect = SELECT_MAP[event.params.model];
	let selectForms = null;

	if (modelsToSelect) {
		selectForms = {};
		await Promise.all(
			Object.entries(modelsToSelect).map(async ([urlModel, { field, backendViewset }]) => {
				if (!field) {
					console.error(`Field name not found for model '${event.params.model}'`);
					return;
				}

				let formData = {};

				const selectSchema = z.object({
					urlModel: z.string(),
					[field]: z.string().uuid().array().optional()
				});

				if (backendViewset) {
					const selectedObjectEndpoint = `${BASE_API_URL}/${backendViewset}/?applied_controls=${event.params.id}`;
					const selectedObjectsReq = await event.fetch(selectedObjectEndpoint);
					let selectedObjects: string[] = [];

					if (selectedObjectsReq.ok) {
						const selectedObjectRes = await selectedObjectsReq.json();
						selectedObjects = selectedObjectRes.results.map((obj) => obj.id);
					} else {
						console.warn(`Failed to fetch selected objects with: ${selectedObjectEndpoint}`);
					}

					formData = {
						urlModel: urlModel,
						[field]: selectedObjects
					};
				} else {
					formData = {
						urlModel: urlModel,
						[field]: object[field] || []
					};
				}

				const selectForm = await superValidate(formData, zod(selectSchema), { errors: false });
				selectForms[urlModel] = selectForm;
			})
		);
	}
	data.selectForms = selectForms;
	data.modelsToSelect = modelsToSelect ?? {};

	if (event.params.model === 'applied-controls') {
		const appliedControlSchema = modelSchema(event.params.model);
		const appliedControl = data.data;
		const initialDataDuplicate = {
			name: appliedControl.name,
			description: appliedControl.description
		};

		const appliedControlDuplicateForm = await superValidate(
			initialDataDuplicate,
			zod(appliedControlSchema),
			{
				errors: false
			}
		);

		data.duplicateForm = appliedControlDuplicateForm;
	}

	return data;
};

export const actions: Actions = {
	create: async (event) => {
		const redirectToWrittenObject = Boolean(event.params.model === 'perimeters');
		return nestedWriteFormAction({ event, action: 'create', redirectToWrittenObject });
	},
	select: async (event) => {
		const formData = await event.request.formData();
		if (!formData) return;

		const modelForm = await superValidate(
			formData,
			zod(
				z.object({
					urlModel: z.string()
				})
			)
		);
		const urlModel = modelForm.data.urlModel;

		if (!urlModel) {
			return fail(400);
		}

		const modelsToSelect = SELECT_MAP[event.params.model as string];
		if (!modelsToSelect) return fail(400);

		const { field, backendViewset, updatedObjectName } = modelsToSelect[urlModel];

		const form = await superValidate(
			formData,
			zod(
				z.object({
					urlModel: z.string(),
					[field]: z.string().uuid().array().optional()
				})
			)
		);

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		const selectedObjects: string[] = form.data[field];
		if (backendViewset) {
			const currentSelectedObjectsReq = await event.fetch(
				`/${backendViewset}?${field}=${event.params.id}`
			);
			if (!currentSelectedObjectsReq.ok) {
				return fail(currentSelectedObjectsReq.status);
			}
			const currentSelectedObjectsRes = await currentSelectedObjectsReq.json();
			const currentSelectedObjects = currentSelectedObjectsRes.results.map((obj) => obj.id);

			const currentSelectedObjectsSet = new Set(currentSelectedObjects);
			const selectedObjectsSet = new Set(selectedObjects);

			const unselectedObjects = currentSelectedObjects.filter((id) => !selectedObjectsSet.has(id));
			const newlySelectedObjects = selectedObjects.filter(
				(id) => !currentSelectedObjectsSet.has(id)
			);

			const selectActions = [
				...newlySelectedObjects.map((id) => [id, true]),
				...unselectedObjects.map((id) => [id, false])
			];

			await Promise.all(
				selectActions.map(async ([id, isSelectAction]) => {
					const endpoint = `${BASE_API_URL}/${backendViewset}/${id}/`;
					const req = await event.fetch(endpoint);
					if (!req.ok) return;

					const obj = await req.json();
					const idListValue = obj[field];
					const idList = idListValue.map((obj) => obj.id);

					const newIdList = isSelectAction
						? [...idList, event.params.id]
						: idList.filter((id) => id !== event.params.id);

					await event.fetch(endpoint, {
						method: 'PATCH',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({
							[field]: newIdList
						})
					});
				})
			);
		} else {
			const formData = {
				id: event.params.id,
				[field]: selectedObjects
			};

			const endpoint = `${BASE_API_URL}/${event.params.model}/${event.params.id}/`;
			const req = await event.fetch(endpoint, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(formData)
			});

			if (!req.ok) {
				console.warn(`Failed to select object with the following endpoint: ${endpoint}`);
				return fail(400, { form });
			}
		}

		setFlash(
			{ type: 'success', message: m.successfullyUpdatedObject({ object: updatedObjectName }) },
			event
		);
		return { form };
	},
	update: async (event) => {
		return defaultWriteFormAction({ event, urlModel: event.params.model, action: 'edit' });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	duplicate: async (event) => {
		const formData = await event.request.formData();

		if (!formData) return;

		const schema = modelSchema((event.params.model + '_duplicate') as string);

		const form = await superValidate(formData, zod(schema));

		const endpoint = `${BASE_API_URL}/${event.params.model}/${event.params.id}/duplicate/`;

		if (!form.valid) {
			console.error(form.errors);
			return fail(400, { form: form });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST',
			body: JSON.stringify(form.data)
		};
		const response = await event.fetch(endpoint, requestInitOptions);

		if (!response.ok) return handleErrorResponse({ event, response, form });

		const modelVerboseName: string = urlParamModelVerboseName(event.params.model as string);
		setFlash(
			{
				type: 'success',
				message: m.successfullyDuplicateObject({
					object: safeTranslate(modelVerboseName).toLowerCase()
				})
			},
			event
		);

		return { form };
	},
	reject: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const rejectForm = await superValidate(formData, zod(schema));

		const urlmodel = rejectForm.data.urlmodel;
		const id = rejectForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/reject/`;

		if (!rejectForm.valid) {
			return fail(400, { form: rejectForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(rejectForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: rejectForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			rejectForm,
			m.successfullyRejectedObject({
				object: safeTranslate(model).toLowerCase(),
				id: id
			})
		);
	},
	submit: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const submitForm = await superValidate(formData, zod(schema));

		const urlmodel = submitForm.data.urlmodel;
		const id = submitForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/submit/`;

		if (!submitForm.valid) {
			return fail(400, { form: submitForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(submitForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: submitForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			submitForm,
			m.successfullyValidatedObject({
				object: safeTranslate(model).toLowerCase(),
				id: id
			})
		);
	},

	draft: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const draftForm = await superValidate(formData, zod(schema));

		const urlmodel = draftForm.data.urlmodel;
		const id = draftForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/draft/`;

		if (!draftForm.valid) {
			return fail(400, { form: draftForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(draftForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: draftForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			draftForm,
			m.successfullyValidatedObject({
				object: safeTranslate(model).toLowerCase(),
				id: id
			})
		);
	},
	accept: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const acceptForm = await superValidate(formData, zod(schema));

		const urlmodel = acceptForm.data.urlmodel;
		const id = acceptForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/accept/`;

		if (!acceptForm.valid) {
			return fail(400, { form: acceptForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(acceptForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: acceptForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			acceptForm,
			m.successfullyValidatedObject({
				object: safeTranslate(model).toLowerCase(),
				id: id
			})
		);
	},
	revoke: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const revokeForm = await superValidate(formData, zod(schema));

		const urlmodel = revokeForm.data.urlmodel;
		const id = revokeForm.data.id;
		const endpoint = `${BASE_API_URL}/${urlmodel}/${id}/revoke/`;

		if (!revokeForm.valid) {
			return fail(400, { form: revokeForm });
		}

		const requestInitOptions: RequestInit = {
			method: 'POST'
		};
		const res = await fetch(endpoint, requestInitOptions);
		if (!res.ok) {
			const response = await res.json();
			if (response.non_field_errors) {
				setError(revokeForm, 'non_field_errors', response.non_field_errors);
			}
			return fail(400, { form: revokeForm });
		}
		const model: string = urlParamModelVerboseName(params.model!);
		// TODO: reference object by name instead of id
		return message(
			revokeForm,
			m.successfullyRevokedObject({
				object: safeTranslate(model).toLowerCase(),
				id: id
			})
		);
	}
};
