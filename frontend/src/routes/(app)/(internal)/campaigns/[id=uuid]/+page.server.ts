import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import {
	defaultWriteFormAction,
	nestedDeleteFormAction,
	nestedWriteFormAction
} from '$lib/utils/actions';
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

	const [targetsRes, dashboardRes] = await Promise.all([
		event.fetch(targetsUrl),
		event.fetch(`${BASE_API_URL}/campaigns/${event.params.id}/dashboard/`)
	]);
	const rows = targetsRes.ok ? ((await targetsRes.json()).results ?? []) : [];
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
