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

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const workflow = await fetchJson(fetch, `${BASE_API_URL}/workflows/workflows/${params.id}/`);
	if (!workflow) error(404, 'Workflow not found');

	const versions: { id: string; version_number: number; status: string }[] = (
		workflow.versions ?? []
	).sort((a: any, b: any) => b.version_number - a.version_number);
	// ?version= pins a specific version (versions panel navigation);
	// default stays draft ?? published ?? first.
	const requestedVersion = url.searchParams.get('version');
	const pinnedVersion = versions.find((v) => v.id === requestedVersion) ?? null;
	// An explicit ?version= that matches nothing is a dead link, not a cue to
	// silently show some other version.
	if (requestedVersion && !pinnedVersion) error(404, 'Workflow version not found');
	const activeVersion =
		pinnedVersion ??
		versions.find((v) => v.status === 'draft') ??
		versions.find((v) => v.status === 'published') ??
		versions[0];
	if (!activeVersion) error(404, 'This workflow has no version');

	const [graph, creatableModelsRaw, readableModelsRaw, updatableModelsRaw] = await Promise.all([
		fetchJson(fetch, `${BASE_API_URL}/workflows/workflow-versions/${activeVersion.id}/graph/`),
		fetchJson(fetch, `${BASE_API_URL}/workflows/workflows/creatable-models/`),
		fetchJson(fetch, `${BASE_API_URL}/workflows/workflows/readable-models/`),
		fetchJson(fetch, `${BASE_API_URL}/workflows/workflows/updatable-models/`)
	]);
	if (!graph) error(404, 'Graph not found');

	// Options for the create_object FK selects, driven by the backend registry.
	// Folders are always fetched: the provisioning actions need them regardless
	// of what the registry declares.
	const creatableModels = listResults(creatableModelsRaw);
	// Only the small relation targets are fetched as pickers; controls,
	// evidences and assets are templated from an upstream node instead.
	const fkEndpoints = [
		...new Set([
			...creatableModels.flatMap((entry: any) => Object.values(entry.fk_fields ?? {})),
			'folders',
			'actors',
			'filtering-labels'
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
		versionPinned: pinnedVersion !== null,
		graph,
		// Task and subprocess authoring are disabled for v1 (not in the palette,
		// blocked at the graph API). No option lists are loaded; the pickers stay
		// empty for any seeded/legacy task or subprocess node.
		taskTemplates: [],
		subprocessCandidates: [],
		creatableModels,
		readableModels: listResults(readableModelsRaw),
		updatableModels: listResults(updatableModelsRaw),
		fkOptions,
		title: workflow.name
	};
};
