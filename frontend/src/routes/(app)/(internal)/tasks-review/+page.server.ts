import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

function clampInt(raw: string | null, fallback: number, min: number, max: number): number {
	const parsed = parseInt(raw || '', 10);
	if (isNaN(parsed)) return fallback;
	return Math.max(min, Math.min(max, parsed));
}

async function safeFetch(fetchFn: typeof fetch, url: string, fallback: unknown = []) {
	try {
		const res = await fetchFn(url);
		if (!res.ok) return fallback;
		return await res.json();
	} catch {
		return fallback;
	}
}

const VALID_GRANULARITIES = ['monthly', 'weekly'] as const;
const VALID_STATUSES = ['completed', 'in_progress', 'pending', 'cancelled'] as const;

export const load: PageServerLoad = async ({ fetch, url }) => {
	const now = new Date();
	const currentYear = now.getFullYear();

	// Validate and clamp numeric params
	const startMonth = clampInt(url.searchParams.get('start_month'), 1, 1, 12);
	const startYear = clampInt(url.searchParams.get('start_year'), currentYear, 1900, 2100);
	const endMonth = clampInt(url.searchParams.get('end_month'), 12, 1, 12);
	const endYear = clampInt(url.searchParams.get('end_year'), currentYear, 1900, 2100);

	// Whitelist filter values
	const rawGranularity = url.searchParams.get('granularity') || 'monthly';
	const granularity = VALID_GRANULARITIES.includes(rawGranularity as any)
		? rawGranularity
		: 'monthly';

	const rawStatus = url.searchParams.get('status') || '';
	const status = rawStatus && VALID_STATUSES.includes(rawStatus as any) ? rawStatus : '';

	const folder = url.searchParams.get('folder') || '';
	const assignedTo = url.searchParams.get('assigned_to') || '';
	const appliedControls = url.searchParams.get('applied_controls') || '';

	// Build API params
	const params = new URLSearchParams();
	params.append('start_month', startMonth.toString());
	params.append('start_year', startYear.toString());
	params.append('end_month', endMonth.toString());
	params.append('end_year', endYear.toString());
	params.append('granularity', granularity);
	if (folder) params.append('folder', folder);
	if (assignedTo) params.append('assigned_to', assignedTo);
	if (appliedControls) params.append('applied_controls', appliedControls);
	if (status) params.append('status', status);

	const endpoint = `${BASE_API_URL}/task-templates/yearly_review/?${params.toString()}`;

	// Streamed with error handling
	const reviewPromise = safeFetch(fetch, endpoint, { folders: [], buckets: [], granularity });

	// Each filter dropdown fetched independently — one failure won't block others
	const foldersPromise = safeFetch(fetch, `${BASE_API_URL}/folders/`);
	const actorsPromise = safeFetch(fetch, `${BASE_API_URL}/actors/`);
	const controlsPromise = safeFetch(fetch, `${BASE_API_URL}/applied-controls/?page_size=500`);

	return {
		reviewData: reviewPromise,
		filterData: Promise.all([foldersPromise, actorsPromise, controlsPromise]).then(
			([foldersData, actorsData, controlsData]) => ({
				allFolders: foldersData.results || foldersData || [],
				allActors: actorsData.results || actorsData || [],
				allAppliedControls: controlsData.results || controlsData || []
			})
		),
		startMonth,
		startYear,
		endMonth,
		endYear,
		selectedFolder: folder,
		selectedGranularity: granularity,
		selectedAssignedTo: assignedTo,
		selectedAppliedControls: appliedControls,
		selectedStatus: status
	};
};
