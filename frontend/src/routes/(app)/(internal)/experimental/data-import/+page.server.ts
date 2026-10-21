import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const [folders, matrices, frameworks, audits, schema] = await Promise.all([
		fetchAllPages(fetch, `${BASE_API_URL}/folders/?content_type=DO&content_type=GL`).catch(
			() => []
		),
		fetchAllPages(fetch, `${BASE_API_URL}/risk-matrices/`).catch(() => []),
		fetchAllPages(fetch, `${BASE_API_URL}/frameworks/`).catch(() => []),
		fetchAllPages(fetch, `${BASE_API_URL}/compliance-assessments/`).catch(() => []),
		fetch(`${BASE_API_URL}/data-wizard/mapping/schema/`)
			.then((r) => r.json())
			.catch(() => ({ model_types: [] }))
	]);
	return {
		title: 'dataWizard',
		folders,
		matrices,
		frameworks,
		audits,
		modelTypes: (schema.model_types ?? []) as string[]
	};
}) satisfies PageServerLoad;
