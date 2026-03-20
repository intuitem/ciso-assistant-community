import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	// Load existing risk matrices for "clone from" feature
	const matricesRes = await fetch(`${BASE_API_URL}/risk-matrices/`);
	const matricesData = await matricesRes.json();
	const matrices = matricesData.results || matricesData;

	// Load existing drafts
	const draftsRes = await fetch(`${BASE_API_URL}/risk-matrix-drafts/`);
	const draftsData = await draftsRes.json();
	const drafts = draftsData.results || draftsData;

	// Load folders
	const foldersRes = await fetch(`${BASE_API_URL}/folders/`);
	const foldersData = await foldersRes.json();
	const folders = foldersData.results || foldersData;

	return { matrices, drafts, folders };
}) satisfies PageServerLoad;
