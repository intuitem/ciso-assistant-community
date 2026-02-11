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

const updateStatus = async (status: string, { fetch, params, cookies }) => {
	const updateData = { status };
	const response = await fetch(`${BASE_API_URL}/task-nodes/${params.id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(updateData)
	});
	if (response.ok) {
		setFlash({ type: 'success', message: m.statusUpdatedSuccessfully() }, cookies);
		return { success: true };
	} else {
		try {
			const error = await response.json();
			return fail(400, { error });
		} catch {
			return fail(400, { error: 'Failed to update status' });
		}
	}
};

export const actions: Actions = {
	addEvidenceRevision: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	pending: async (event) => updateStatus('pending', event),
	inProgress: async (event) => updateStatus('in_progress', event),
	cancelled: async (event) => updateStatus('cancelled', event),
	completed: async (event) => updateStatus('completed', event),
	updateObservation: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const observation = formData.get('observation');
		if (typeof observation !== 'string') {
			return fail(400, { error: 'Invalid observation value' });
		}

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
	},
	removeEvidence: async (event) => {
		const formData = await event.request.formData();
		const evidenceId = formData.get('evidenceId');
		const move = formData.get('move');

		if (typeof evidenceId !== 'string') {
			return fail(400, { error: 'Invalid evidence ID' });
		}

		const response = await event.fetch(
			`${BASE_API_URL}/task-nodes/${event.params.id}/remove_evidence/`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ evidence_id: evidenceId, move: move === 'true' })
			}
		);

		if (response.ok) {
			return { success: true };
		}
		const error = await response.json();
		return fail(400, { error });
	},
	updateDueDate: async ({ request, fetch, params, cookies }) => {
		const formData = await request.formData();
		const dueDate = formData.get('due_date');
		if (typeof dueDate !== 'string') {
			return fail(400, { error: 'Invalid due date value' });
		}

		const updateData = {
			due_date: dueDate
		};

		const response = await fetch(`${BASE_API_URL}/task-nodes/${params.id}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(updateData)
		});

		if (response.ok) {
			setFlash({ type: 'success', message: m.dueDateUpdatedSuccessfully() }, cookies);
			return { success: true };
		} else {
			const error = await response.json();
			return fail(400, { error });
		}
	}
};
