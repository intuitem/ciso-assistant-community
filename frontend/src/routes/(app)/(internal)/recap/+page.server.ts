import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import type { Perimeter } from '$lib/utils/types';
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
	localName?: string;
	value: number;
	itemStyle: Record<string, unknown>;
}

interface RequirementAssessmentDonutItem extends Omit<DonutItem, 'name'> {
	name: (typeof REQUIREMENT_ASSESSMENT_STATUS)[number];
	percentage: string;
}

interface PerimeterAnalytics extends Perimeter {
	overallCompliance: {
		values: RequirementAssessmentDonutItem[];
		total: number;
	};
}

export const load: PageServerLoad = async ({ locals, fetch }) => {
	const perimeters: PerimeterAnalytics[] = await fetch(`${BASE_API_URL}/perimeters/`)
		.then((res) => res.json())
		.then(async (perimeters) => {
			if (perimeters && Array.isArray(perimeters.results)) {
				const perimeterPromises = perimeters.results.map(async (perimeter) => {
					try {
						const complianceAssessmentsResponse = await fetch(
							`${BASE_API_URL}/compliance-assessments/?perimeter=${perimeter.id}`
						);
						const complianceAssessmentsData = await complianceAssessmentsResponse.json();

						if (complianceAssessmentsData && Array.isArray(complianceAssessmentsData.results)) {
							const updatedAssessmentsPromises = complianceAssessmentsData.results.map(
								async (complianceAssessment) => {
									try {
										const [donutDataResponse, globalScoreResponse] = await Promise.all([
											fetch(
												`${BASE_API_URL}/compliance-assessments/${complianceAssessment.id}/donut_data/`
											),
											fetch(
												`${BASE_API_URL}/compliance-assessments/${complianceAssessment.id}/global_score/`
											)
										]);

										const [donutData, globalScoreData] = await Promise.all([
											donutDataResponse.json(),
											globalScoreResponse.json()
										]);

										complianceAssessment.donut = donutData;
										complianceAssessment.globalScore = globalScoreData;
										return complianceAssessment;
									} catch (error) {
										console.error('Error fetching data for compliance assessment:', error);
										throw error;
									}
								}
							);

							const updatedAssessments = await Promise.all(updatedAssessmentsPromises);
							perimeter.compliance_assessments = updatedAssessments;
							return perimeter;
						} else {
							throw new Error('Compliance assessments results not found or not an array');
						}
					} catch (error) {
						console.error('Error fetching compliance assessments:', error);
						throw error;
					}
				});

				return Promise.all(perimeterPromises);
			} else {
				throw new Error('Perimeters results not found or not an array');
			}
		})
		.catch((error) => {
			console.error('Failed to load perimeters:', error);
			return []; // Ensure always returning an array of Record<string, any>
		});

	if (perimeters) {
		perimeters.forEach((perimeter) => {
			// Initialize an object to hold the aggregated donut data
			const aggregatedDonutData: {
				values: RequirementAssessmentDonutItem[];
				total: number;
			} = {
				values: [],
				total: 0
			};

			// Iterate through each compliance assessment of the perimeter
			perimeter.compliance_assessments.forEach((compliance_assessment: Record<string, any>) => {
				// Process the donut data of each assessment
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
			});

			// Calculate the total sum of all values
			const totalValue = aggregatedDonutData.values.reduce((sum, item) => sum + item.value, 0);

			// Calculate and store the percentage for each item
			aggregatedDonutData.values = aggregatedDonutData.values.map((item) => ({
				...item,
				percentage: totalValue > 0 ? ((item.value / totalValue) * 100).toFixed(1) : '0'
			}));

			// Assign the aggregated donut data to the perimeter
			perimeter.overallCompliance = aggregatedDonutData;
		});
	}

	return {
		perimeters,
		user: locals.user,
		title: m.recap()
	};
};
