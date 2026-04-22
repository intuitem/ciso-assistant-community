import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

const REQUIREMENT_ASSESSMENT_STATUS = [
	'compliant',
	'partially_compliant',
	'in_progress',
	'non_compliant',
	'not_applicable',
	'to_do'
] as const;

interface DonutItem {
	name: string;
	localName: string;
	value: number;
	itemStyle: {
		color: string;
	};
}

interface DonutFieldData {
	values: DonutItem[];
	labels: string[];
}

interface DonutData {
	result: DonutFieldData;
	status: DonutFieldData;
	extended_result: DonutFieldData;
}

interface ComplianceAssessmentRecapData {
	id: string;
	name: string;
	folder: {
		id: string;
		name: string;
	};
	framework: {
		str: string;
	};
	donut: DonutData;
	global_score: {
		implementation_score: number;
		documentation_score: number;
		maturity_score: number;
		min_score: number;
		max_score: number;
	};
}

interface RequirementAssessmentDonutItem extends Omit<DonutItem, 'name'> {
	name: (typeof REQUIREMENT_ASSESSMENT_STATUS)[number];
	percentage: string;
}

interface FolderAnalytics {
	id: string;
	name: string;
	compliance_assessments: ComplianceAssessmentRecapData[];
	overallCompliance: {
		values: RequirementAssessmentDonutItem[];
		total: number;
	};
}

/** Set the `overallCompliance` field value for a `folder` `FolderAnalytics`. */
function setFolderOverallCompliance(folder: FolderAnalytics) {
	// Initialize an object to hold the aggregated donut data
	const aggregatedDonutData: {
		values: RequirementAssessmentDonutItem[];
		total: number;
	} = {
		values: [],
		total: 0
	};

	// Iterate through each compliance assessment of the folder
	if (folder.compliance_assessments) {
		folder.compliance_assessments.forEach((compliance_assessment: Record<string, any>) => {
			// Process the donut data of each assessment
			if (compliance_assessment.donut?.result?.values) {
				compliance_assessment.donut.result.values.forEach(
					(donutItem: RequirementAssessmentDonutItem) => {
						// Find the corresponding item in the aggregated data
						const aggregatedItem: RequirementAssessmentDonutItem | undefined =
							aggregatedDonutData.values.find((item) => item.name === donutItem.name);
						if (aggregatedItem) {
							// If the item already exists, increment its value
							aggregatedItem.value += donutItem.value;
						} else {
							// If it's a new item, add it to the aggregated data
							aggregatedDonutData.values.push({ ...donutItem });
						}
					}
				);
			}
		});
	}

	// Calculate the total sum of all values
	const totalValue = aggregatedDonutData.values.reduce((sum, item) => sum + item.value, 0);

	// Calculate and store the percentage for each item
	aggregatedDonutData.values = aggregatedDonutData.values.map((item) => ({
		...item,
		percentage: totalValue > 0 ? ((item.value / totalValue) * 100).toFixed(1) : '0'
	}));

	// Assign the aggregated donut data to the folder
	folder.overallCompliance = aggregatedDonutData;
}

export const load: PageServerLoad = async ({ locals, fetch }) => {
	const res = await fetch(`${BASE_API_URL}/compliance-assessments/recap/`);
	let folderRecaps: FolderAnalytics[] = [];

	if (res.ok) {
		const recapData: ComplianceAssessmentRecapData[] = await res.json();

		/** Used to GROUP compliance assessment data BY folder. */
		const folderToRecap: Record<string, FolderAnalytics> = {};

		for (const complianceAssessmentData of recapData) {
			const folderId = complianceAssessmentData.folder.id;
			const folderName = complianceAssessmentData.folder.name;

			const folderRecap = folderToRecap[folderId] ?? {
				id: folderId,
				name: folderName,
				compliance_assessments: []
			};

			folderRecap.compliance_assessments.push(complianceAssessmentData);
			folderToRecap[folderId] = folderRecap;

			folderRecaps = Object.values(folderToRecap);
		}
	} else {
		console.error(`An error occured while fetching recap data.`);
	}

	folderRecaps.forEach(setFolderOverallCompliance);

	return {
		folderRecaps,
		user: locals.user,
		title: m.recap()
	};
};
