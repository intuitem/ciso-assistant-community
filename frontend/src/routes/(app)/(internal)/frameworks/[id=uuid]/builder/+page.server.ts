import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const [framework, nodesRes, questionsRes] = await Promise.all([
		fetch(`${BASE_API_URL}/frameworks/${params.id}/object/`),
		fetch(
			`${BASE_API_URL}/requirement-nodes/?framework=${params.id}&ordering=order_id&page_size=9999`
		),
		fetch(`${BASE_API_URL}/questions/?framework=${params.id}&ordering=order&page_size=9999`)
	]);

	const frameworkData = await framework.json();
	const nodesData = await nodesRes.json();
	const questionsData = await questionsRes.json();

	return {
		framework: frameworkData,
		requirementNodes: nodesData.results ?? nodesData,
		questions: questionsData.results ?? questionsData,
		isImported: !!frameworkData.library,
		hasEditingDraft: !!frameworkData.has_editing_draft,
		title: `Builder - ${frameworkData.name}`
	};
}) satisfies PageServerLoad;
