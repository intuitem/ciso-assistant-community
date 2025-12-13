import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	// Load applied controls with dates for Gantt visualization
	const appliedControlsEndpoint = `${BASE_API_URL}/applied-controls/`;
	const appliedControlsRes = await fetch(appliedControlsEndpoint);
	const appliedControlsData = await appliedControlsRes.json();
	const appliedControls = appliedControlsData.results || appliedControlsData;

	// Load task nodes for Gantt visualization
	const taskNodesEndpoint = `${BASE_API_URL}/task-nodes/`;
	const taskNodesRes = await fetch(taskNodesEndpoint);
	const taskNodesData = await taskNodesRes.json();
	const taskNodes = taskNodesData.results || taskNodesData;

	// Load folders for filtering
	const foldersEndpoint = `${BASE_API_URL}/folders/`;
	const foldersRes = await fetch(foldersEndpoint);
	const foldersData = await foldersRes.json();
	const folders = foldersData.results || foldersData;

	return { appliedControls, taskNodes, folders };
}) satisfies PageServerLoad;
