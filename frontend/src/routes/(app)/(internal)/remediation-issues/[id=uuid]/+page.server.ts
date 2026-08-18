import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import { safeTranslate } from '$lib/utils/i18n';
import type { Actions } from '@sveltejs/kit';
import { fail } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	return loadDetail({
		event,
		model: getModelInfo('remediation-issues'),
		id: event.params.id
	});
};

async function callIssueAction(
	{ fetch, params, cookies }: { fetch: any; params: any; cookies: any },
	action: string,
	payload: Record<string, unknown>,
	successMessage: string
) {
	const response = await fetch(`${BASE_API_URL}/remediation-issues/${params.id}/${action}/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	if (response.ok) {
		setFlash({ type: 'success', message: successMessage }, cookies);
		return { success: true };
	}
	const body = await response.json().catch(() => ({}));
	const errorKey = body?.error ?? 'anErrorOccurred';
	setFlash({ type: 'error', message: safeTranslate(errorKey) }, cookies);
	return fail(response.status, { error: errorKey });
}

export const actions: Actions = {
	proposeCommitment: async (event) => {
		const formData = await event.request.formData();
		return callIssueAction(
			event,
			'propose_commitment',
			{
				text: formData.get('text'),
				due_date: formData.get('due_date') || null,
				based_on_version_id: formData.get('based_on_version_id') || null
			},
			m.commitmentProposed()
		);
	},
	setAcceptance: async (event) => {
		const formData = await event.request.formData();
		return callIssueAction(
			event,
			'set_acceptance',
			{
				state: formData.get('state'),
				side: formData.get('side') || undefined
			},
			m.acceptanceRecorded()
		);
	},
	submitReview: async (event) => {
		return callIssueAction(event, 'submit_review', {}, m.submittedForReview());
	},
	close: async (event) => {
		const formData = await event.request.formData();
		return callIssueAction(
			event,
			'close',
			{
				resolution: formData.get('resolution'),
				closure_justification: formData.get('closure_justification')
			},
			m.issueClosed()
		);
	},
	cancel: async (event) => {
		const formData = await event.request.formData();
		return callIssueAction(
			event,
			'cancel',
			{ cancellation_reason: formData.get('cancellation_reason') },
			m.issueCancelled()
		);
	},
	reopen: async (event) => {
		const formData = await event.request.formData();
		return callIssueAction(
			event,
			'reopen',
			{ status: formData.get('status') },
			m.issueReopened()
		);
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
