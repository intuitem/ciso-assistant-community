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
	handleErrorResponse
} from '$lib/utils/actions';
import { modelSchema } from '$lib/utils/schemas';

import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('task-nodes');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	return data;
};

export const actions: Actions = {
	addEvidenceRevision: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	pending: async ({ request, fetch, params, cookies }) => {
		const updateData = {
			status: 'pending'
		};

		const response = await fetch(`${BASE_API_URL}/task-nodes/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.statusUpdatedSuccessfully() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},
	inProgress: async ({ request, fetch, params, cookies }) => {
		const updateData = {
			status: 'in_progress'
		};

		const response = await fetch(`${BASE_API_URL}/task-nodes/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.statusUpdatedSuccessfully() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},
	cancelled: async ({ request, fetch, params, cookies }) => {
		const updateData = {
			status: 'cancelled'
		};

		const response = await fetch(`${BASE_API_URL}/task-nodes/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.statusUpdatedSuccessfully() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},
	completed: async ({ request, fetch, params, cookies }) => {
		const updateData = {
			status: 'completed'
		};

		const response = await fetch(`${BASE_API_URL}/task-nodes/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.statusUpdatedSuccessfully() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	},
	updateObservation: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const observation = formData.get('observation') as string;

		const updateData = {
			observation
		};

		const response = await fetch(`${BASE_API_URL}/task-nodes/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.observationUpdatedSuccessfully() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	}
};
