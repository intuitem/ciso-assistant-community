import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';

interface TimelineEntry {
	model: string;
	id: string;
	name: string;
	folder: string;
	start_date?: string | null;
	eta?: string | null;
	due_date?: string | null;
	created_at?: string | null;
	expiration_date?: string | null;
	progress_field?: number;
	progress?: number;
	owners?: string[];
}

// Backend model keys -> ganttData keys consumed by +page.svelte
const MODEL_KEYS = {
	applied_controls: 'appliedControls',
	compliance_assessments: 'complianceAssessments',
	risk_assessments: 'riskAssessments',
	business_impact_analyses: 'businessImpactAnalyses',
	findings_assessments: 'findingsAssessments',
	security_exceptions: 'securityExceptions'
} as const;

type GanttKey = (typeof MODEL_KEYS)[keyof typeof MODEL_KEYS];

export const load: PageServerLoad = async ({ fetch }) => {
	// Folders are lightweight — await them so the page shell renders immediately
	const folders = await fetchAllPages(fetch, `${BASE_API_URL}/folders/`).catch(() => []);

	// Stream the timeline entries (one aggregate request) so the page can show
	// a spinner. Reshape to the per-model arrays the component expects.
	// Never let this promise reject: a rejected streamed promise is an
	// unhandled rejection on the node server. Resolve with an error flag and
	// let the page render its error state instead.
	const emptyGroups = (): Record<GanttKey, Record<string, unknown>[]> => ({
		appliedControls: [],
		complianceAssessments: [],
		riskAssessments: [],
		businessImpactAnalyses: [],
		findingsAssessments: [],
		securityExceptions: []
	});
	const ganttData = fetch(`${BASE_API_URL}/insights-timeline/`)
		.then(async (res) => {
			if (!res.ok) {
				throw new Error(`Failed to load timeline entries (${res.status})`);
			}
			const entries: TimelineEntry[] = await res.json();
			const grouped = emptyGroups();
			for (const entry of entries) {
				const key = MODEL_KEYS[entry.model as keyof typeof MODEL_KEYS];
				if (!key) continue;
				grouped[key].push({
					...entry,
					// The component reads owner names as {str} objects (old serializer shape)
					owners: (entry.owners ?? []).map((str) => ({ str }))
				});
			}
			return { ...grouped, error: false };
		})
		.catch((err) => {
			console.error('Failed to load timeline entries:', err);
			return { ...emptyGroups(), error: true };
		});

	return {
		folders,
		ganttData
	};
};
