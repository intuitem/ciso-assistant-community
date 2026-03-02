import { getModelInfo } from '$lib/utils/crud';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction, nestedWriteFormAction } from '$lib/utils/actions';
import { loadDetail } from '$lib/utils/load';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { modelSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async (event) => {
	const URLModel = 'operating-modes';
	const model = getModelInfo(URLModel);
	const updateSchema = modelSchema(URLModel);
	const objectEndpoint = `${BASE_API_URL}/${model.endpointUrl}/${event.params.id}/object/`;
	const eaEndpoint = `${BASE_API_URL}/ebios-rm/elementary-actions/`;
	const killChainEndpoint = `${BASE_API_URL}/ebios-rm/kill-chains/?operating_mode=${event.params.id}`;

	const [detail, objectResponse, eaRes, kcRes] = await Promise.all([
		loadDetail({ event, model: model, id: event.params.id }),
		event.fetch(objectEndpoint),
		event.fetch(eaEndpoint),
		event.fetch(killChainEndpoint)
	]);

	const object = await objectResponse.json();
	const updateForm = await superValidate(object, zod(updateSchema), { errors: false });
	const eaData = await eaRes.json();
	const kcData = await kcRes.json();

	return {
		...detail,
		updateForm,
		model,
		object,
		elementaryActions: eaData.results ?? eaData,
		killChainSteps: kcData.results ?? kcData,
		operatingModeId: event.params.id
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
		return defaultWriteFormAction({ event, urlModel: 'operating-modes', action: 'edit' });
	},
	saveGraph: async (event) => {
		const formData = await event.request.formData();
		const killChainStepsJson = formData.get('kill_chain_steps');

		if (!killChainStepsJson || typeof killChainStepsJson !== 'string') {
			return fail(400, { error: 'Missing kill_chain_steps data' });
		}

		let killChainSteps;
		try {
			killChainSteps = JSON.parse(killChainStepsJson);
		} catch {
			return fail(400, { error: 'Invalid JSON in kill_chain_steps' });
		}

		const endpoint = `${BASE_API_URL}/ebios-rm/operating-modes/${event.params.id}/save_graph/`;

		const response = await event.fetch(endpoint, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ kill_chain_steps: killChainSteps })
		});

		if (response.ok) {
			const graphData = await response.json();
			setFlash(
				{
					type: 'success',
					message: m.successfullyUpdatedObject({ object: m.operatingMode().toLowerCase() })
				},
				event
			);
			return { success: true, graphData };
		} else {
			const errData = await response.json();
			setFlash(
				{
					type: 'error',
					message: errData.errors?.join(', ') ?? m.errorOccurred()
				},
				event
			);
			return fail(response.status, { error: errData.errors });
		}
	}
};
