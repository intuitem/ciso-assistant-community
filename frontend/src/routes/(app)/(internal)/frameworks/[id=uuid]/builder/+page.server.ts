import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const [framework, nodesRes, questionsRes, controlsRes, threatsRes] = await Promise.all([
		fetch(`${BASE_API_URL}/frameworks/${params.id}/object/`),
		fetch(
			`${BASE_API_URL}/requirement-nodes/?framework=${params.id}&ordering=order_id&page_size=9999`
		),
		fetch(`${BASE_API_URL}/questions/?framework=${params.id}&ordering=order&page_size=9999`),
		// Catalogs the node picker offers to link. Bounded sets, so loaded up
		// front rather than searched per keystroke.
		fetch(`${BASE_API_URL}/reference-controls/?ordering=name&page_size=9999`),
		fetch(`${BASE_API_URL}/threats/?ordering=name&page_size=9999`)
	]);

	const frameworkData = await framework.json();
	const nodesData = await nodesRes.json();
	const questionsData = await questionsRes.json();
	const controlsData = await controlsRes.json();
	const threatsData = await threatsRes.json();

	return {
		framework: frameworkData,
		requirementNodes: nodesData.results ?? nodesData,
		questions: questionsData.results ?? questionsData,
		referenceControlCatalog: controlsData.results ?? controlsData,
		threatCatalog: threatsData.results ?? threatsData,
		isImported: !!frameworkData.library,
		hasEditingDraft: !!frameworkData.has_editing_draft,
		title: `Builder - ${frameworkData.name}`
	};
}) satisfies PageServerLoad;
