import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const detail = await loadDetail({
		event,
		model: getModelInfo('projects'),
		id: event.params.id
	});

	const [statusRes, healthRes, priorityRes, actorRes, collectionRes, projectRes] =
		await Promise.all([
			event.fetch(
				`${BASE_API_URL}/terminologies/?field_path=project.status&is_visible=true&limit=100`
			),
			event.fetch(
				`${BASE_API_URL}/terminologies/?field_path=project.health&is_visible=true&limit=100`
			),
			event.fetch(`${BASE_API_URL}/pmbok/projects/priority/`),
			event.fetch(`${BASE_API_URL}/actors/?user__is_third_party=False&limit=200`),
			event.fetch(`${BASE_API_URL}/pmbok/generic-collections/?limit=200`),
			event.fetch(`${BASE_API_URL}/pmbok/projects/?limit=200`)
		]);

	const statusOptions = statusRes.ok ? ((await statusRes.json()).results ?? []) : [];
	const healthOptions = healthRes.ok ? ((await healthRes.json()).results ?? []) : [];
	const priorityDict = priorityRes.ok ? await priorityRes.json() : {};
	const priorityOptions = Object.entries(priorityDict).map(([value, label]) => ({
		value: parseInt(value),
		label: label as string
	}));
	const actorOptions = actorRes.ok ? ((await actorRes.json()).results ?? []) : [];
	const collectionOptions = collectionRes.ok ? ((await collectionRes.json()).results ?? []) : [];
	const allProjects = projectRes.ok ? ((await projectRes.json()).results ?? []) : [];
	const projectOptions = allProjects.filter((p: any) => p.id !== event.params.id);

	return {
		...detail,
		statusOptions,
		healthOptions,
		priorityOptions,
		actorOptions,
		collectionOptions,
		projectOptions
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
