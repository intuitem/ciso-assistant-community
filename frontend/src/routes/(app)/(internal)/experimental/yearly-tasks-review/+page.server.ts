import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const now = new Date();
	const currentYear = now.getFullYear();

	// Get query parameters with defaults
	const startMonth = url.searchParams.get('start_month') || '1';
	const startYear = url.searchParams.get('start_year') || currentYear.toString();
	const endMonth = url.searchParams.get('end_month') || '12';
	const endYear = url.searchParams.get('end_year') || currentYear.toString();
	const folder = url.searchParams.get('folder') || '';
	const granularity = url.searchParams.get('granularity') || 'monthly';
	const assignedTo = url.searchParams.get('assigned_to') || '';
	const appliedControls = url.searchParams.get('applied_controls') || '';
	const status = url.searchParams.get('status') || '';

	// Build endpoint with filters
	const params = new URLSearchParams();
	params.append('start_month', startMonth);
	params.append('start_year', startYear);
	params.append('end_month', endMonth);
	params.append('end_year', endYear);
	params.append('granularity', granularity);
	if (folder) params.append('folder', folder);
	if (assignedTo) params.append('assigned_to', assignedTo);
	if (appliedControls) params.append('applied_controls', appliedControls);
	if (status) params.append('status', status);

	const endpoint = `${BASE_API_URL}/task-templates/yearly_review/?${params.toString()}`;

	const [res, foldersRes, actorsRes, appliedControlsRes] = await Promise.all([
		fetch(endpoint),
		fetch(`${BASE_API_URL}/folders/`),
		fetch(`${BASE_API_URL}/actors/`),
		fetch(`${BASE_API_URL}/applied-controls/?page_size=500`)
	]);

	const data = await res.json();
	const foldersData = await foldersRes.json();
	const actorsData = await actorsRes.json();
	const appliedControlsData = await appliedControlsRes.json();

	return {
		folders: data.folders || [],
		buckets: data.buckets || [],
		granularity: data.granularity || 'monthly',
		allFolders: foldersData.results || foldersData,
		allActors: actorsData.results || actorsData,
		allAppliedControls: appliedControlsData.results || appliedControlsData,
		startMonth: parseInt(startMonth),
		startYear: parseInt(startYear),
		endMonth: parseInt(endMonth),
		endYear: parseInt(endYear),
		selectedFolder: folder,
		selectedAssignedTo: assignedTo,
		selectedAppliedControls: appliedControls,
		selectedStatus: status
	};
};
