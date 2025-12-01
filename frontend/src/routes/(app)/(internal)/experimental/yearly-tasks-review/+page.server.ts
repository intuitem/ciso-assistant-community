import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	// Get query parameters
	const year = url.searchParams.get('year') || new Date().getFullYear().toString();
	const folder = url.searchParams.get('folder') || '';

	// Build endpoint with filters
	const params = new URLSearchParams();
	if (year) params.append('year', year);
	if (folder) params.append('folder', folder);

	const endpoint = `${BASE_API_URL}/task-templates/yearly_review/?${params.toString()}`;

	const res = await fetch(endpoint);
	const data = await res.json();

	// Fetch all folders for the filter dropdown
	const foldersRes = await fetch(`${BASE_API_URL}/folders/`);
	const foldersData = await foldersRes.json();
	const allFolders = foldersData.results || foldersData;

	return {
		folders: data,
		allFolders,
		selectedYear: year,
		selectedFolder: folder
	};
};
