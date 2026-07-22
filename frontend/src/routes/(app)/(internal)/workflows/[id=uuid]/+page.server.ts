import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

async function fetchJson(fetchFn: typeof fetch, url: string) {
	const res = await fetchFn(url);
	if (!res.ok) return null;
	return res.json();
}

function listResults(data: unknown): any[] {
	if (Array.isArray(data)) return data;
	if (data && typeof data === 'object' && 'results' in data)
		return (data as { results: any[] }).results;
	return [];
}

export const load: PageServerLoad = async ({ fetch, params }) => {
	const workflow = await fetchJson(fetch, `${BASE_API_URL}/workflows/workflows/${params.id}/`);
	if (!workflow) error(404, 'Workflow not found');

	const versions: { id: string; version_number: number; status: string }[] = (
		workflow.versions ?? []
	).sort((a: any, b: any) => b.version_number - a.version_number);
	const activeVersion =
		versions.find((v) => v.status === 'draft') ??
		versions.find((v) => v.status === 'published') ??
		versions[0];
	if (!activeVersion) error(404, 'This workflow has no version');

	const [graph, roles, actors, taskTemplates, workflows, creatableModelsRaw] = await Promise.all([
		fetchJson(fetch, `${BASE_API_URL}/workflows/workflow-versions/${activeVersion.id}/graph/`),
		fetchJson(fetch, `${BASE_API_URL}/pmbok/responsibility-roles/?is_visible=true`),
		fetchJson(fetch, `${BASE_API_URL}/actors/`),
		fetchJson(fetch, `${BASE_API_URL}/task-templates/`),
		fetchJson(fetch, `${BASE_API_URL}/workflows/workflows/`),
		fetchJson(fetch, `${BASE_API_URL}/workflows/workflows/creatable-models/`)
	]);
	if (!graph) error(404, 'Graph not found');

	// Options for the create_object FK selects, driven by the backend registry.
	// Folders are always fetched: the provisioning actions need them regardless
	// of what the registry declares.
	const creatableModels = listResults(creatableModelsRaw);
	const fkEndpoints = [
		...new Set([
			...creatableModels.flatMap((entry: any) => Object.values(entry.fk_fields ?? {})),
			'folders'
		])
	] as string[];
	const fkOptions: Record<string, any[]> = {};
	await Promise.all(
		fkEndpoints.map(async (endpoint) => {
			fkOptions[endpoint] = listResults(await fetchJson(fetch, `${BASE_API_URL}/${endpoint}/`));
		})
	);

	return {
		workflow,
		versions,
		activeVersion,
		graph,
		roles: listResults(roles),
		actors: listResults(actors),
		taskTemplates: listResults(taskTemplates),
		// A workflow can't be its own subprocess.
		subprocessCandidates: listResults(workflows).filter((w: any) => w.id !== workflow.id),
		creatableModels,
		fkOptions,
		title: workflow.name
	};
};
