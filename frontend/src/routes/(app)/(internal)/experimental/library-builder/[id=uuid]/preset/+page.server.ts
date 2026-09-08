import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const draftRes = await fetch(`${BASE_API_URL}/library-drafts/${params.id}/`);
	if (!draftRes.ok) {
		throw error(draftRes.status, 'Library draft not found');
	}
	const draft = await draftRes.json();

	// Scaffold references target loaded-library URNs (see the retired
	// standalone preset editor): same picker data as before. fetchAllPages
	// throws on a non-OK response, so the pickers fall back to [] instead of
	// receiving a DRF error object.
	const fetchList = (url: string): Promise<any[]> => fetchAllPages(fetch, url).catch(() => []);
	const [frameworks, riskMatrices, frameworkDetails] = await Promise.all([
		fetchList(`${BASE_API_URL}/loaded-libraries/?object_type=framework&ordering=name`),
		fetchList(`${BASE_API_URL}/loaded-libraries/?object_type=risk_matrix&ordering=name`),
		fetchList(`${BASE_API_URL}/frameworks/?ordering=name`)
	]);

	// Shape the moved preset-editor page expects. The preset has its own
	// name/description, falling back to the library's (legacy one-to-one
	// preset libraries).
	const presetObject = draft.content?.preset ?? {};
	const preset = {
		id: draft.id,
		name: presetObject.name ?? draft.name,
		description: presetObject.description ?? draft.description,
		is_user_authored: true,
		editing_version: draft.identity_locked ? 2 : 1
	};

	return { draft, preset, frameworks, riskMatrices, frameworkDetails };
};
