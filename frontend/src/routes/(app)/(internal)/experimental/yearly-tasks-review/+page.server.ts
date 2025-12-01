import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	// Get current date for defaults
	const now = new Date();
	const currentYear = now.getFullYear();

	// Get query parameters with defaults (full current year)
	const startMonth = url.searchParams.get('start_month') || '1';
	const startYear = url.searchParams.get('start_year') || currentYear.toString();
	const endMonth = url.searchParams.get('end_month') || '12';
	const endYear = url.searchParams.get('end_year') || currentYear.toString();
	const folder = url.searchParams.get('folder') || '';

	// Build endpoint with filters
	const params = new URLSearchParams();
	params.append('start_month', startMonth);
	params.append('start_year', startYear);
	params.append('end_month', endMonth);
	params.append('end_year', endYear);
	if (folder) params.append('folder', folder);

	const endpoint = `${BASE_API_URL}/task-templates/yearly_review/?${params.toString()}`;

	const res = await fetch(endpoint);
	const data = await res.json();

	// Fetch all folders for the filter dropdown
	const foldersRes = await fetch(`${BASE_API_URL}/folders/`);
	const foldersData = await foldersRes.json();
	const allFolders = foldersData.results || foldersData;

	return {
		folders: data.folders || [],
		allFolders,
		startMonth: parseInt(startMonth),
		startYear: parseInt(startYear),
		endMonth: parseInt(endMonth),
		endYear: parseInt(endYear),
		selectedFolder: folder
	};
};
