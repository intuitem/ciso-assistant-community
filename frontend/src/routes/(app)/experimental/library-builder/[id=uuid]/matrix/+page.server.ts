import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const draftRes = await fetch(`${BASE_API_URL}/library-drafts/${params.id}/`);
	if (!draftRes.ok) {
		throw error(draftRes.status, 'Library draft not found');
	}
	const draft = await draftRes.json();

	const matrices = (draft.content?.risk_matrices ?? []) as Record<string, unknown>[];
	const matrixUrn = url.searchParams.get('matrix_urn')?.toLowerCase();
	const matrix = matrixUrn
		? matrices.find((m) => String(m.urn).toLowerCase() === matrixUrn)
		: matrices[0];
	if (!matrix) {
		throw error(404, 'No such risk matrix in this draft');
	}

	return { draft, matrix };
};
