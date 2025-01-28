import { BASE_API_URL } from '$lib/utils/constants';
import { composerSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import type { Project } from '$lib/utils/types';
import { TODAY } from '$lib/utils/constants';
import * as m from '$paraglide/messages';

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

export const load: PageServerLoad = async ({ locals, fetch }) => {
	const urls = [
		`${BASE_API_URL}/applied-controls/per_status/`,
		`${BASE_API_URL}/risk-assessments/per_status/`,
		`${BASE_API_URL}/compliance-assessments/per_status/`,
		`${BASE_API_URL}/risk-scenarios/per_status/`,
		`${BASE_API_URL}/applied-controls/todo/`,
		`${BASE_API_URL}/get_counters/`,
		`${BASE_API_URL}/get_metrics/`,
		`${BASE_API_URL}/risk-matrices/used/`,
		`${BASE_API_URL}/frameworks/used/`,
		`${BASE_API_URL}/risk-scenarios/count_per_level/`,
		`${BASE_API_URL}/threats/threats_count/`,
		`${BASE_API_URL}/applied-controls/to_review/`,
		`${BASE_API_URL}/risk-acceptances/to_review/`,
		`${BASE_API_URL}/risk-assessments/`,
		`${BASE_API_URL}/projects/`
	];

	const responses = await Promise.all(urls.map((url) => fetch(url)));
	const [
		appliedControlStatusRes,
		riskAssessmentsRes,
		complianceAssessmentsRes,
		riskScenariosRes,
		ordAppliedControlsRes,
		countersRes,
		metricsRes,
		usedRiskMatricesRes,
		usedFrameworksRes,
		risksCountPerLevelRes,
		threatsCountRes,
		measuresToReviewRes,
		acceptancesToReviewRes,
		riskAssessmentsRes2,
		projectsRes
	] = await Promise.all(responses.map((res) => res.json()));

	function timeState(date: string) {
		const eta = new Date(date);
		if (eta.getTime() > TODAY.getTime()) {
			return { name: 'incoming', hexcolor: '#93c5fd' };
		} else if (eta.getTime() < TODAY.getTime()) {
			return { name: 'outdated', hexcolor: '#f87171' };
		} else {
			return { name: 'today', hexcolor: '#fbbf24' };
		}
	}

	const ordAppliedControls = ordAppliedControlsRes.results.map((control) => ({
		...control,
		state: timeState(control.eta)
	}));

	const measuresToReview = measuresToReviewRes.results.map((measure) => ({
		...measure,
		state: timeState(measure.expiry_date)
	}));

	const acceptancesToReview = acceptancesToReviewRes.results.map((acceptance) => ({
		...acceptance,
		state: timeState(acceptance.expiry_date)
	}));

	const projects = await Promise.all(
		projectsRes.results.map(async (project) => {
			try {
				const complianceAssessmentsRes = await fetch(
					`${BASE_API_URL}/compliance-assessments/?project=${project.id}`
				).then((res) => res.json());

				if (Array.isArray(complianceAssessmentsRes.results)) {
					project.compliance_assessments = await Promise.all(
						complianceAssessmentsRes.results.map(async (complianceAssessment) => {
							const [donutData, globalScore] = await Promise.all([
								fetch(
									`${BASE_API_URL}/compliance-assessments/${complianceAssessment.id}/donut_data/`
								).then((res) => res.json()),
								fetch(
									`${BASE_API_URL}/compliance-assessments/${complianceAssessment.id}/global_score/`
								).then((res) => res.json())
							]);
							return {
								...complianceAssessment,
								donut: donutData,
								globalScore
							};
						})
					);
				}
				return project;
			} catch (error) {
				console.error('Error processing project compliance assessments', error);
				return project;
			}
		})
	);

	// Prepare donut aggregation
	projects.forEach((project) => {
		const aggregatedDonutData: {
			values: RequirementAssessmentDonutItem[];
			total: number;
		} = {
			values: [],
			total: 0
		};
		project.compliance_assessments.forEach((assessment) => {
			assessment.donut.result.values.forEach((donutItem) => {
				const existingItem = aggregatedDonutData.values.find(
					(item) => item.name === donutItem.name
				);
				if (existingItem) {
					existingItem.value += donutItem.value;
				} else {
					aggregatedDonutData.values.push({ ...donutItem });
				}
			});
		});
		const totalValue = aggregatedDonutData.values.reduce((sum, item) => sum + item.value, 0);
		aggregatedDonutData.values = aggregatedDonutData.values.map((item) => ({
			...item,
			percentage: totalValue > 0 ? ((item.value / totalValue) * 100).toFixed(1) : '0'
		}));
		project.overallCompliance = aggregatedDonutData;
	});

	const composerForm = await superValidate(zod(composerSchema));

	return {
		composerForm,
		usedRiskMatrices: usedRiskMatricesRes.results,
		usedFrameworks: usedFrameworksRes.results,
		riskAssessmentsPerStatus: riskAssessmentsRes.results,
		complianceAssessmentsPerStatus: complianceAssessmentsRes.results,
		riskScenariosPerStatus: riskScenariosRes.results,
		risks_count_per_level: risksCountPerLevelRes.results,
		threats_count: threatsCountRes,
		measures_to_review: measuresToReview,
		acceptances_to_review: acceptancesToReview,
		risk_assessments: riskAssessmentsRes2.results,
		get_counters: countersRes.results,
		measures: ordAppliedControls,
		applied_control_status: appliedControlStatusRes.results,
		projects,
		user: locals.user,
		metrics: metricsRes.results,
		title: m.analytics()
	};
};
