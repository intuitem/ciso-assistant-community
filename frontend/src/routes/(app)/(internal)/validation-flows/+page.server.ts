import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo, urlParamModelSelectFields } from '$lib/utils/crud';
import { formatSelectFieldData } from '$lib/utils/load';
import { modelSchema } from '$lib/utils/schemas';
import type { ModelInfo } from '$lib/utils/types';
import { fail, type Actions } from '@sveltejs/kit';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { setFlash } from 'sveltekit-flash-message/server';
import { z } from 'zod';
import { m } from '$paraglide/messages';
import type { PageServerLoad, RequestEvent } from './$types';

const URL_MODEL = 'validation-flows';
const TABS = ['received', 'sent', 'history', 'all'] as const;
type Tab = (typeof TABS)[number];

export const load: PageServerLoad = async ({ fetch, url }) => {
	const requestedTab = url.searchParams.get('tab') as Tab | null;

	const deleteForm = await superValidate(zod(z.object({ id: z.string().uuid() })));
	const createForm = await superValidate(zod(modelSchema(URL_MODEL)));
	const model: ModelInfo = getModelInfo(URL_MODEL);

	const selectOptions: Record<string, any> = {};
	for (const selectField of urlParamModelSelectFields(URL_MODEL)) {
		if (selectField.detail) continue;
		const res = await fetch(`${BASE_API_URL}/${URL_MODEL}/${selectField.field}/`);
		if (res.ok) {
			selectOptions[selectField.field] = formatSelectFieldData(await res.json(), selectField);
		}
	}
	model['selectOptions'] = selectOptions;

	const countsResponse = await fetch(`${BASE_API_URL}/${URL_MODEL}/inbox_counts/`);
	const counts = countsResponse.ok
		? await countsResponse.json()
		: { received: 0, sent: 0, history: 0 };

	// Without an explicit tab, land on the first queue that has something in it —
	// requesters would otherwise always open on an empty "received".
	const tab: Tab =
		requestedTab && TABS.includes(requestedTab)
			? requestedTab
			: ((['received', 'sent', 'history'] as Tab[]).find((candidate) => counts[candidate] > 0) ??
				'received');

	// The "all" tab is served by ModelTable, which fetches on its own.
	const flows =
		tab === 'all'
			? []
			: await fetch(`${BASE_API_URL}/${URL_MODEL}/?scope=${tab}&ordering=-created_at`)
					.then((res) => (res.ok ? res.json() : { results: [] }))
					.then((data) => data.results ?? []);

	return {
		tab,
		counts,
		flows,
		createForm,
		deleteForm,
		model,
		URLModel: URL_MODEL,
		modelDescriptionKey: 'validationFlowsPageDescription'
	};
};

const TRANSITIONS: Record<string, { status: string; message: () => string }> = {
	approve: { status: 'accepted', message: () => m.validationApproved() },
	reject: { status: 'rejected', message: () => m.validationRejected() },
	revoke: { status: 'revoked', message: () => m.validationRevoked() },
	drop: { status: 'dropped', message: () => m.validationDropped() },
	request_changes: { status: 'change_requested', message: () => m.changesRequested() },
	resubmit: { status: 'submitted', message: () => m.validationResubmitted() }
};

async function transition(event: RequestEvent, action: keyof typeof TRANSITIONS) {
	const formData = await event.request.formData();
	const id = formData.get('id') as string;
	if (!id) return fail(400, { error: 'Missing validation flow id' });

	const response = await event.fetch(`${BASE_API_URL}/${URL_MODEL}/${id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			status: TRANSITIONS[action].status,
			event_notes: formData.get('notes') as string
		})
	});

	if (!response.ok) {
		return fail(400, { error: await response.json().catch(() => ({})) });
	}
	setFlash({ type: 'success', message: TRANSITIONS[action].message() }, event);
	return { success: true };
}

export const actions: Actions = {
	create: async (event) => defaultWriteFormAction({ event, urlModel: URL_MODEL, action: 'create' }),
	delete: async (event) => defaultDeleteFormAction({ event, urlModel: URL_MODEL }),
	approve: async (event) => transition(event, 'approve'),
	reject: async (event) => transition(event, 'reject'),
	revoke: async (event) => transition(event, 'revoke'),
	drop: async (event) => transition(event, 'drop'),
	request_changes: async (event) => transition(event, 'request_changes'),
	resubmit: async (event) => transition(event, 'resubmit')
};
