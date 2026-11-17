import { BASE_API_URL } from '#lib/utils/constants.js';
import { getModelInfo, urlParamModelVerboseName } from '#lib/utils/crud.js';

import { safeTranslate } from '#lib/utils/i18n.js';
import { m } from '#paraglide/messages.js';

import { fail, type Actions } from '@sveltejs/kit';
import { message, setError, superValidate } from 'sveltekit-superforms';
import { setFlash } from 'sveltekit-flash-message/server';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import {
	nestedDeleteFormAction,
	nestedWriteFormAction,
	handleErrorResponse
} from '#lib/utils/actions.js';
import { modelSchema } from '#lib/utils/schemas.js';

import { loadDetail } from '#lib/utils/load.js';
import {
	fetchNeighbour,
	fetchOccurrenceHistory,
	type OccurrenceSummary
} from '#lib/utils/taskOccurrences.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('task-nodes');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	// A recurrent task's occurrence shows the same history as its task, plus the
	// occurrences just before and after it for the previous / next buttons. Those
	// are asked for separately: the viewed occurrence can sit outside the history.
	const node = data.data;
	const dueDate = typeof node?.due_date === 'string' ? node.due_date.slice(0, 10) : null;
	const taskTemplateId = node?.task_template?.id;
	let history: OccurrenceSummary[] = [];
	let previousOccurrence: OccurrenceSummary | null = null;
	let nextOccurrence: OccurrenceSummary | null = null;
	// Any of the requests failing: the page says so rather than showing a
	// history with holes or greying out a button that has somewhere to go.
	let occurrencesFailed = false;
	if (node?.is_recurrent && taskTemplateId) {
		const [occurrences, previous, next] = await Promise.all([
			fetchOccurrenceHistory(event.fetch, taskTemplateId),
			dueDate ? fetchNeighbour(event.fetch, taskTemplateId, dueDate, true) : null,
			dueDate ? fetchNeighbour(event.fetch, taskTemplateId, dueDate, false) : null
		]);
		history = [...occurrences.pastOccurrences, ...occurrences.upcomingOccurrences].map(
			({ id, due_date, status }) => ({ id, due_date, status })
		);
		previousOccurrence = previous?.occurrence ?? null;
		nextOccurrence = next?.occurrence ?? null;
		occurrencesFailed =
			occurrences.occurrencesFailed || previous?.failed === true || next?.failed === true;
	}

	return { ...data, history, previousOccurrence, nextOccurrence, occurrencesFailed };
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
			try {
				const error = await response.json();
				const rawMessage = error.due_date
					? Array.isArray(error.due_date)
						? error.due_date[0]
						: error.due_date
					: error.error || error.detail || m.anErrorOccurred();
				const errorMessage = safeTranslate(rawMessage);
				setFlash({ type: 'error', message: errorMessage }, cookies);
				return fail(400, { error });
			} catch {
				setFlash({ type: 'error', message: m.anErrorOccurred() }, cookies);
				return fail(400, { error: m.anErrorOccurred() });
			}
		}
	}
};
