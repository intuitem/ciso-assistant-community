import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	// Load applied controls with dates for Gantt visualization
	const appliedControlsEndpoint = `${BASE_API_URL}/applied-controls/`;
	const appliedControlsRes = await fetch(appliedControlsEndpoint);
	const appliedControlsData = await appliedControlsRes.json();
	const appliedControls = appliedControlsData.results || appliedControlsData;

	// Load folders for filtering
	const foldersEndpoint = `${BASE_API_URL}/folders/`;
	const foldersRes = await fetch(foldersEndpoint);
	const foldersData = await foldersRes.json();
	const folders = foldersData.results || foldersData;

	return { appliedControls, folders };
}) satisfies PageServerLoad;
