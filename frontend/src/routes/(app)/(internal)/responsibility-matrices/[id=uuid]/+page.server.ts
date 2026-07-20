import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import { z } from 'zod';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';

const linkedObjectsSchema = z.object({
	assets: z.array(z.string().uuid()).default([]),
	applied_controls: z.array(z.string().uuid()).default([]),
	task_templates: z.array(z.string().uuid()).default([]),
	risk_assessments: z.array(z.string().uuid()).default([]),
	compliance_assessments: z.array(z.string().uuid()).default([]),
	findings_assessments: z.array(z.string().uuid()).default([]),
	business_impact_analyses: z.array(z.string().uuid()).default([])
});

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('responsibility-matrices'),
		id: event.params.id
	});

	const matrixId = event.params.id;

	// Eager fetches are limited to what the page renders on mount.
	// Link-object lookup lists (assets, applied-controls, task-templates,
	// risk/compliance/findings assessments, BIAs) are NOT fetched here —
	// AutocompleteSelect inside the activity drawer fetches them on demand
	// when the user actually opens a drawer, and the PATCH response on
	// update-activity returns the Read shape so we can rehydrate links
	// without a separate pool.
	const [activities, matrixActors, assignments, allActors] = await Promise.all([
		fetchAllPages(
			event.fetch,
			`${BASE_API_URL}/pmbok/responsibility-matrix-activities/?matrix=${matrixId}&ordering=order`
		).catch(() => []),
		fetchAllPages(
			event.fetch,
			`${BASE_API_URL}/pmbok/responsibility-matrix-actors/?matrix=${matrixId}&ordering=order`
		).catch(() => []),
		fetchAllPages(
			event.fetch,
			`${BASE_API_URL}/pmbok/responsibility-assignments/?activity__matrix=${matrixId}`
		).catch(() => []),
		fetchAllPages(event.fetch, `${BASE_API_URL}/actors/?ordering=user__email`).catch(() => [])
	]);

	const linkedObjectsForm = await superValidate(zod(linkedObjectsSchema), { errors: false });

	return {
		...detailData,
		activities,
		matrixActors,
		assignments,
		allActors,
		linkedObjectsForm
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
