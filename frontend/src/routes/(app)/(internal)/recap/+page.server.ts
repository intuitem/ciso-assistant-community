import { BASE_API_URL, complianceResultColorMap } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

const RESULT_ORDER = [
	'not_assessed',
	'partially_compliant',
	'non_compliant',
	'compliant',
	'not_applicable'
] as const;

type ResultKey = (typeof RESULT_ORDER)[number];
type ResultCounts = Partial<Record<ResultKey, number>>;

interface RawRecapAssessment {
	id: string;
	name: string;
	framework_name: string;
	result_counts: ResultCounts;
	global_score: {
		maturity_score: number | null;
		max_score: number;
	};
}

interface RawRecapFolder {
	id: string;
	name: string;
	compliance_assessments: RawRecapAssessment[];
}

function buildDonutValues(resultCounts: ResultCounts) {
	return RESULT_ORDER.map((result) => ({
		name: result,
		value: resultCounts[result] ?? 0,
		itemStyle: { color: complianceResultColorMap[result] ?? '#d1d5db' }
	}));
}

function buildOverallCompliance(complianceAssessments: RawRecapAssessment[]) {
	const counts = Object.fromEntries(RESULT_ORDER.map((result) => [result, 0])) as Record<ResultKey, number>;

	for (const assessment of complianceAssessments) {
		for (const result of RESULT_ORDER) {
			counts[result] += assessment.result_counts[result] ?? 0;
		}
	}

	const total = Object.values(counts).reduce((sum, value) => sum + value, 0);

	return {
		values: RESULT_ORDER.map((result) => ({
			name: result,
			value: counts[result],
			itemStyle: { color: complianceResultColorMap[result] ?? '#d1d5db' },
			percentage: total > 0 ? ((counts[result] / total) * 100).toFixed(1) : '0'
		})),
		total
	};
}

function shapeFolderForRecap(folder: RawRecapFolder) {
	const complianceAssessments = folder.compliance_assessments.map((assessment) => ({
		id: assessment.id,
		name: assessment.name,
		framework: {
			str: assessment.framework_name
		},
		donut: {
			result: {
				values: buildDonutValues(assessment.result_counts)
			}
		},
		globalScore: assessment.global_score
	}));

	return {
		id: folder.id,
		name: folder.name,
		compliance_assessments: complianceAssessments,
		overallCompliance: buildOverallCompliance(folder.compliance_assessments)
	};
}

export const load: PageServerLoad = async ({ locals, fetch }) => {
	// The backend now returns only recap raw data (counts + score summaries).
	// Presentation details such as colors, percentages, and donut wiring are
	// rebuilt here on the frontend side.
	const folders = await fetch(`${BASE_API_URL}/compliance-assessments/recap/`)
		.then(async (res) => {
			if (!res.ok) {
				throw new Error(`Failed to load recap data: ${res.status} ${res.statusText}`);
			}
			return res.json();
		})
		.then((data) => ((data.results ?? []) as RawRecapFolder[]).map(shapeFolderForRecap))
		.catch((error) => {
			// Keep the page renderable even if the recap endpoint fails temporarily.
			console.error('Failed to load recap:', error);
			return [];
		});

	return {
		folders,
		user: locals.user,
		title: m.recap()
	};
};
