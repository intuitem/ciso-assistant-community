import { BASE_API_URL } from '#lib/utils/constants.js';
import {
	isGranularity,
	orderWindow,
	rollingWindow,
	type Granularity
} from '#lib/utils/control-plan.js';
import { fetchAllPages } from '#lib/utils/pagination.js';
import { m } from '#paraglide/messages.js';
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

const VALID_STATUSES = ['completed', 'in_progress', 'pending', 'cancelled', 'overdue'] as const;
const PERIOD_PARAMS = ['start_month', 'start_year', 'end_month', 'end_year'] as const;

export const load: PageServerLoad = async ({ fetch, url }) => {
	// Whitelist filter values
	const rawGranularity = url.searchParams.get('granularity');
	const granularity: Granularity = isGranularity(rawGranularity) ? rawGranularity : 'monthly';

	// Without an explicit period the page follows today: a rolling window sized
	// for the granularity. Each missing bound falls back to that window.
	const rolling = PERIOD_PARAMS.every((name) => !url.searchParams.has(name));
	const fallback = rollingWindow(new Date(), granularity);

	// Validate and clamp numeric params
	// A bound given alone can land past the fallback of the other one: keep
	// the range ordered, or the grid would have rows and no period.
	const { startMonth, startYear, endMonth, endYear } = orderWindow({
		startMonth: clampInt(url.searchParams.get('start_month'), fallback.startMonth, 1, 12),
		startYear: clampInt(url.searchParams.get('start_year'), fallback.startYear, 1900, 2100),
		endMonth: clampInt(url.searchParams.get('end_month'), fallback.endMonth, 1, 12),
		endYear: clampInt(url.searchParams.get('end_year'), fallback.endYear, 1900, 2100)
	});

	// Several statuses may be selected: ?status=overdue&status=pending
	const requested = new Set(url.searchParams.getAll('status'));
	const statuses = VALID_STATUSES.filter((status) => requested.has(status));

	const folder = url.searchParams.get('folder') || '';
	// A domain stands for itself and everything below it, unless switched off.
	const includeSubfolders = url.searchParams.get('include_subfolders') !== 'false';
	const assignedTo = url.searchParams.get('assigned_to') || '';
	const appliedControls = url.searchParams.get('applied_controls') || '';

	// Build API params
	const params = new URLSearchParams();
	params.append('start_month', startMonth.toString());
	params.append('start_year', startYear.toString());
	params.append('end_month', endMonth.toString());
	params.append('end_year', endYear.toString());
	params.append('granularity', granularity);
	if (folder) {
		params.append('folder', folder);
		if (includeSubfolders) params.append('include_subfolders', 'true');
	}
	if (assignedTo) params.append('assigned_to', assignedTo);
	if (appliedControls) params.append('applied_controls', appliedControls);
	for (const status of statuses) params.append('status', status);

	const endpoint = `${BASE_API_URL}/task-templates/yearly_review/?${params.toString()}`;

	// Streamed with error handling
	const reviewPromise = safeFetch(fetch, endpoint, { folders: [], buckets: [], granularity });

	// Domains and applied controls load their own options client-side (domain
	// tree, server-side search): only the actors are fetched here.
	const actorsPromise = fetchAllPages(fetch, `${BASE_API_URL}/actors/`).catch(() => []);

	return {
		title: m.tasksReview(),
		reviewData: reviewPromise,
		filterData: actorsPromise.then((allActors) => ({ allActors })),
		startMonth,
		startYear,
		endMonth,
		endYear,
		rolling,
		selectedFolder: folder,
		includeSubfolders,
		selectedGranularity: granularity,
		selectedAssignedTo: assignedTo,
		selectedAppliedControls: appliedControls,
		selectedStatuses: statuses as string[]
	};
};
