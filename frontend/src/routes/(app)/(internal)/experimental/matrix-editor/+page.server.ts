import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	// Load all risk matrices (published ones for "clone from", ones with editing_draft for "resume")
	const matricesRes = await fetch(`${BASE_API_URL}/risk-matrices/`);
	const matricesData = await matricesRes.json();
	const allMatrices = matricesData.results || matricesData;

	// Split: published matrices (for clone) vs matrices with active drafts
	const matrices = allMatrices.filter((m: any) => m.is_published);
	const drafts = allMatrices.filter((m: any) => m.editing_draft !== null);

	// Load folders
	const foldersRes = await fetch(`${BASE_API_URL}/folders/`);
	const foldersData = await foldersRes.json();
	const folders = foldersData.results || foldersData;

	return { matrices, drafts, folders };
}) satisfies PageServerLoad;
