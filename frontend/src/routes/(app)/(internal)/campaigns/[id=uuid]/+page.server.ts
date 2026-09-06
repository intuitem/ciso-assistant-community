import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import {
	defaultWriteFormAction,
	nestedDeleteFormAction,
	nestedWriteFormAction
} from '$lib/utils/actions';
import { safeTranslate } from '$lib/utils/i18n';
import { m } from '$paraglide/messages';
import { fail } from '@sveltejs/kit';
import { setFlash } from 'sveltekit-flash-message/server';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { Actions, PageServerLoad } from './$types';

type Target = {
	id: string;
	label: string;
	name: string;
	progress: number;
	updated_at: string | null;
	href: string;
	secondary: string | null;
};

export const load: PageServerLoad = async (event) => {
	const detail = await loadDetail({
		event,
		model: getModelInfo('campaigns'),
		id: event.params.id
	});
	const thirdParty = detail.data?.kind === 'third_party';

	// A third-party campaign is steered through the entity assessment: it carries the
	// entity, the reviewers and the conclusion. Internal ones stop at the audit.
	const targetsUrl = thirdParty
		? `${BASE_API_URL}/entity-assessments/?compliance_assessment__campaign=${event.params.id}`
		: `${BASE_API_URL}/compliance-assessments/?campaign=${event.params.id}`;

	// Every target is rendered, and a campaign can exceed one page.
	const [rows, dashboardRes] = await Promise.all([
		fetchAllPages<Record<string, any>>(event.fetch, targetsUrl).catch(() => []),
		event.fetch(`${BASE_API_URL}/campaigns/${event.params.id}/dashboard/`)
	]);
	const dashboard = dashboardRes.ok
		? await dashboardRes.json()
		: { trend: [], assignments: { per_status: {}, flagged: 0 } };

	const targets: Target[] = rows.map((row: Record<string, any>) => ({
		id: row.id,
		// What the campaign actually targets: an entity for a third party, the
		// perimeter the audit was launched on otherwise.
		label: (thirdParty ? row.entity?.str : (row.perimeter?.str ?? row.folder?.str)) ?? row.name,
		name: row.name,
		progress: (thirdParty ? row.completion : row.progress) ?? 0,
		updated_at: row.updated_at ?? null,
		href: thirdParty ? `/entity-assessments/${row.id}` : `/compliance-assessments/${row.id}`,
		secondary: thirdParty ? (row.assignment_status ?? null) : (row.status ?? null)
	}));

	// Only one of the two reverse tabs applies to a given campaign.
	delete detail.relatedModels[thirdParty ? 'compliance-assessments' : 'entity-assessments'];

	return { ...detail, targets, thirdParty, dashboard };
};

export const actions: Actions = {
	start: async (event) => {
		// Returned as a superform like ?/mailing: only a form result triggers
		// invalidateAll, so the status would otherwise look unchanged.
		const schema = z.object({ urlmodel: z.string(), id: z.string().uuid() });
		const form = await superValidate(await event.request.formData(), zod(schema));

		const res = await event.fetch(`${BASE_API_URL}/campaigns/${event.params.id}/start/`, {
			method: 'POST'
		});
		const body = await res.json().catch(() => ({}));
		if (!res.ok) {
			setFlash({ type: 'error', message: safeTranslate(body.error ?? 'anErrorOccurred') }, event);
			return fail(res.status, { form });
		}
		const missing = body.unassigned?.length ?? 0;
		// One flash, not two: the second would replace the first and the count would
		// be the thing lost.
		setFlash(
			missing
				? {
						type: 'warning',
						message: m.campaignStartedWithUnassigned({ count: body.started, missing })
					}
				: { type: 'success', message: m.campaignStarted({ count: body.started }) },
			event
		);
		return { form };
	},

	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create', redirectToWrittenObject: false });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	update: async (event) => {
		return defaultWriteFormAction({ event, urlModel: 'campaigns', action: 'edit' });
	}
};
