import { BASE_API_URL } from '$lib/utils/constants';
import { composerSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
import { TODAY } from '$lib/utils/constants';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async ({ locals, fetch }) => {
	const req_applied_control_status = await fetch(`${BASE_API_URL}/applied-controls/per_status/`);
	const applied_control_status = await req_applied_control_status.json();

	const req_task_template_status = await fetch(`${BASE_API_URL}/task-templates/per_status/`);
	const task_template_status = await req_task_template_status.json();

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

	const getCounters = async () => {
		try {
			const response = await fetch(`${BASE_API_URL}/get_counters/`);
			const data = await response.json();
			return data.results;
		} catch (error) {
			console.error('failed to fetch or parse counters:', error);
			return null;
		}
	};

	const getCombinedAssessmentsStatus = async () => {
		try {
			const response = await fetch(`${BASE_API_URL}/get_combined_assessments_status/`);
			const data = await response.json();
			return data.results;
		} catch (error) {
			console.error('failed to fetch or parse combined assessments status:', error);
			return null;
		}
	};
	const getMetrics = async () => {
		try {
			const response = await fetch(`${BASE_API_URL}/get_metrics/`);
			const data = await response.json();
			return data.results;
		} catch (error) {
			console.error('Failed to fetch or parse metrics:', error);
			return null;
		}
	};

	const usedRiskMatrices: { id: string; name: string; risk_assessments_count: number }[] =
		await fetch(`${BASE_API_URL}/risk-matrices/used/`)
			.then((res) => res.json())
			.then((res) => res.results);
	const usedFrameworks: { id: string; name: string; compliance_assessments_count: number }[] =
		await fetch(`${BASE_API_URL}/frameworks/used/`)
			.then((res) => res.json())
			.then((res) => res.results);
	const req_get_risks_count_per_level = await fetch(
		`${BASE_API_URL}/risk-scenarios/count_per_level/`
	);
	const risks_count_per_level: {
		current: Record<string, any>[];
		residual: Record<string, any>[];
		inherent?: Record<string, any>[];
	} = await req_get_risks_count_per_level.json().then((res) => res.results);

	const threats_count = await fetch(`${BASE_API_URL}/threats/threats_count/`).then((res) =>
		res.json()
	);

	const qualifications_count = await fetch(
		`${BASE_API_URL}/risk-scenarios/qualifications_count/`
	).then((res) => res.json());

	const req_risk_assessments = await fetch(`${BASE_API_URL}/risk-assessments/`);
	const risk_assessments = await req_risk_assessments.json();

	const composerForm = await superValidate(zod(composerSchema));

	const complianceAnalytics = await fetch(`${BASE_API_URL}/compliance-assessments/analytics/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch compliance analytics:', error);
			return {};
		});

	const getGovernanceCalendarData = async () => {
		try {
			const currentYear = new Date().getFullYear();
			const response = await fetch(
				`${BASE_API_URL}/get_governance_calendar_data/?year=${currentYear}`
			);
			const data = await response.json();
			return data.results;
		} catch (error) {
			console.error('Failed to fetch governance calendar data:', error);
			return [];
		}
	};

	const getOperationsAnalytics = async () => {
		try {
			const detectionData = await fetch(`${BASE_API_URL}/incidents/detection_breakdown/`)
				.then((res) => res.json())
				.catch((error) => {
					console.error('Failed to fetch incident detection breakdown:', error);
					return { results: [] };
				});

			const monthlyData = await fetch(`${BASE_API_URL}/incidents/monthly_metrics/`)
				.then((res) => res.json())
				.catch((error) => {
					console.error('Failed to fetch monthly incident metrics:', error);
					return { results: { months: [], monthly_counts: [], cumulative_counts: [] } };
				});

			const summaryData = await fetch(`${BASE_API_URL}/incidents/summary_stats/`)
				.then((res) => res.json())
				.catch((error) => {
					console.error('Failed to fetch incident summary stats:', error);
					return { results: { total_incidents: 0, incidents_this_month: 0, open_incidents: 0 } };
				});

			const severityData = await fetch(`${BASE_API_URL}/incidents/severity_breakdown/`)
				.then((res) => res.json())
				.catch((error) => {
					console.error('Failed to fetch incident severity breakdown:', error);
					return { results: [] };
				});

			const qualificationsData = await fetch(`${BASE_API_URL}/incidents/qualifications_breakdown/`)
				.then((res) => res.json())
				.catch((error) => {
					console.error('Failed to fetch incident qualifications breakdown:', error);
					return { results: { labels: [], values: [] } };
				});

			const exceptionSankeyData = await fetch(`${BASE_API_URL}/security-exceptions/sankey_data/`)
				.then((res) => res.json())
				.catch((error) => {
					console.error('Failed to fetch security exception Sankey data:', error);
					return { results: { nodes: [], links: [] } };
				});

			const sunburstData = await fetch(`${BASE_API_URL}/applied-controls/sunburst_data/`)
				.then((res) => res.json())
				.catch((error) => {
					console.error('Failed to fetch applied controls sunburst data:', error);
					return { results: [] };
				});

			const findingsSankeyData = await fetch(`${BASE_API_URL}/findings/sankey_data/`)
				.then((res) => res.json())
				.catch((error) => {
					console.error('Failed to fetch findings Sankey data:', error);
					return { results: { nodes: [], links: [] } };
				});

			return {
				incident_detection_breakdown: detectionData.results,
				monthly_metrics: monthlyData.results,
				summary_stats: summaryData.results,
				severity_breakdown: severityData.results,
				qualifications_breakdown: qualificationsData.results,
				exception_sankey: exceptionSankeyData.results,
				applied_controls_sunburst: sunburstData.results,
				findings_sankey: findingsSankeyData.results
			};
		} catch (error) {
			console.error('Failed to fetch operations analytics:', error);
			return null;
		}
	};

	const getVulnerabilitySankeyData = async () => {
		try {
			const response = await fetch(`${BASE_API_URL}/vulnerabilities/sankey_data/`);
			const data = await response.json();
			return data;
		} catch (error) {
			console.error('Failed to fetch vulnerability sankey data:', error);
			return [];
		}
	};

	const getFindingsAssessmentSunburstData = async () => {
		try {
			const response = await fetch(`${BASE_API_URL}/findings-assessments/sunburst_data/`);
			const data = await response.json();
			return data;
		} catch (error) {
			console.error('Failed to fetch findings assessment sunburst data:', error);
			return [];
		}
	};

	return {
		composerForm,
		usedRiskMatrices,
		usedFrameworks,
		riskAssessmentsPerStatus,
		complianceAssessmentsPerStatus,
		riskScenariosPerStatus,
		risks_count_per_level,
		threats_count,
		qualifications_count,
		risk_assessments: risk_assessments.results,
		applied_control_status: applied_control_status.results,
		task_template_status: task_template_status.results,
		complianceAnalytics,
		user: locals.user,
		title: m.analytics(),
		stream: {
			metrics: getMetrics(),
			counters: getCounters(),
			combinedAssessmentsStatus: getCombinedAssessmentsStatus(),
			governanceCalendarData: getGovernanceCalendarData(),
			operationsAnalytics: getOperationsAnalytics(),
			vulnerabilitySankeyData: getVulnerabilitySankeyData(),
			findingsAssessmentSunburstData: getFindingsAssessmentSunburstData()
		}
	};
};
