import { BASE_API_URL } from '$lib/utils/constants';
import { composerSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
	const req_applied_control_status = await fetch(`${BASE_API_URL}/applied-controls/per_status/`);
	const applied_control_status = await req_applied_control_status.json();

	const riskAssessmentsPerStatus = await fetch(`${BASE_API_URL}/risk-assessments/per_status/`)
		.then((res) => res.json())
		.then((res) => res.results);
	const complianceAssessmentsPerStatus = await fetch(
		`${BASE_API_URL}/compliance-assessments/per_status/`
	)
		.then((res) => res.json())
		.then((res) => res.results);
	const riskScenariosPerStatus = await fetch(`${BASE_API_URL}/risk-scenarios/per_status/`)
		.then((res) => res.json())
		.then((res) => res.results);

	const req_ord_applied_controls = await fetch(`${BASE_API_URL}/applied-controls/todo/`);
	const ord_applied_controls = await req_ord_applied_controls.json();

	const req_get_counters = await fetch(`${BASE_API_URL}/get_counters/`);
	const counters = await req_get_counters.json();

	const usedRiskMatrices = await fetch(`${BASE_API_URL}/risk-matrices/used/`)
		.then((res) => res.json())
		.then((res) => res.results);
	const usedFrameworks = await fetch(`${BASE_API_URL}/frameworks/used/`)
		.then((res) => res.json())
		.then((res) => res.results);

	const req_get_risks_count_per_level = await fetch(
		`${BASE_API_URL}/risk-scenarios/count_per_level/`
	);
	const risks_count_per_level = await req_get_risks_count_per_level.json();

	const req_get_measures_to_review = await fetch(`${BASE_API_URL}/applied-controls/to_review/`);
	const measures_to_review = await req_get_measures_to_review.json();

	const req_get_acceptances_to_review = await fetch(`${BASE_API_URL}/risk-acceptances/to_review/`);
	const acceptances_to_review = await req_get_acceptances_to_review.json();

	const req_risk_assessments = await fetch(`${BASE_API_URL}/risk-assessments/`);
	const risk_assessments = await req_risk_assessments.json();

	const projects = await fetch(`${BASE_API_URL}/projects/`)
    .then((res) => res.json())
    .then(async (projects) => {
        if (projects && Array.isArray(projects.results)) {
            const projectPromises = projects.results.map(async (project) => {
                try {
                    const complianceAssessmentsResponse = await fetch(`${BASE_API_URL}/compliance-assessments/?project=${project.id}`);
                    const complianceAssessmentsData = await complianceAssessmentsResponse.json();

                    if (complianceAssessmentsData && Array.isArray(complianceAssessmentsData.results)) {
                        const updatedAssessmentsPromises = complianceAssessmentsData.results.map(async (complianceAssessment) => {
                            try {
                                const [donutDataResponse, globalScoreResponse] = await Promise.all([
                                    fetch(`${BASE_API_URL}/compliance-assessments/${complianceAssessment.id}/donut_data/`),
                                    fetch(`${BASE_API_URL}/compliance-assessments/${complianceAssessment.id}/global_score/`)
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
                        });

                        const updatedAssessments = await Promise.all(updatedAssessmentsPromises);
                        project.compliance_assessments = updatedAssessments;
                        return project;
                    } else {
                        throw new Error('Compliance assessments results not found or not an array');
                    }
                } catch (error) {
                    console.error('Error fetching compliance assessments:', error);
                    throw error;
                }
            });

            return Promise.all(projectPromises);
        } else {
            throw new Error('Projects results not found or not an array');
        }
    })
    .catch((error) => console.error('Error:', error));

	if (projects) {
		projects.forEach((project) => {
			// Initialize an object to hold the aggregated donut data
			const aggregatedDonutData = {
				values: [],
				total: 0
			};

			// Iterate through each compliance assessment of the project
			project.compliance_assessments.forEach((compliance_assessment) => {
				// Process the donut data of each assessment
				compliance_assessment.donut.values.forEach((donutItem) => {
					// Find the corresponding item in the aggregated data
					const aggregatedItem = aggregatedDonutData.values.find(
						(item) => item.name === donutItem.name
					);

					if (aggregatedItem) {
						// If the item already exists, increment its value
						aggregatedItem.value += donutItem.value;
					} else {
						// If it's a new item, add it to the aggregated data
						aggregatedDonutData.values.push({ ...donutItem });
					}
				});
			});

			// Calculate the total sum of all values
			const totalValue = aggregatedDonutData.values.reduce((sum, item) => sum + item.value, 0);

			// Calculate and store the percentage for each item
			aggregatedDonutData.values = aggregatedDonutData.values.map((item) => ({
				...item,
				percentage: totalValue > 0 ? parseFloat((item.value / totalValue) * 100).toFixed(1) : 0
			}));

			// Assign the aggregated donut data to the project
			project.overallCompliance = aggregatedDonutData;
		});
	}

	const composerForm = await superValidate(zod(composerSchema));

	return {
		composerForm,
		usedRiskMatrices,
		usedFrameworks,
		riskAssessmentsPerStatus,
		complianceAssessmentsPerStatus,
		riskScenariosPerStatus,
		risks_level: risks_count_per_level.results,
		measures_to_review: measures_to_review.results,
		acceptances_to_review: acceptances_to_review.results,
		risk_assessments: risk_assessments.results,
		get_counters: counters.results,
		measures: ord_applied_controls.results,
		applied_control_status: applied_control_status.results,
		projects,
		user: locals.user
	};
};
