import { BASE_API_URL } from '$lib/utils/constants';
import { composerSchema } from '$lib/utils/schemas';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from './$types';
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

	// Start all streaming fetches immediately (before returning from load)
	const currentYear = new Date().getFullYear();

	const metricsPromise = fetch(`${BASE_API_URL}/get_metrics/`)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('Failed to fetch or parse metrics:', error);
			return null;
		});

	const countersPromise = fetch(`${BASE_API_URL}/get_counters/`)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('failed to fetch or parse counters:', error);
			return null;
		});

	const combinedAssessmentsStatusPromise = fetch(`${BASE_API_URL}/get_combined_assessments_status/`)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('failed to fetch or parse combined assessments status:', error);
			return null;
		});

	const governanceCalendarDataPromise = fetch(
		`${BASE_API_URL}/get_governance_calendar_data/?year=${currentYear}`
	)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('Failed to fetch governance calendar data:', error);
			return [];
		});

	const vulnerabilitySankeyDataPromise = fetch(`${BASE_API_URL}/vulnerabilities/sankey_data/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch vulnerability sankey data:', error);
			return [];
		});

	const findingsAssessmentSunburstDataPromise = fetch(
		`${BASE_API_URL}/findings-assessments/sunburst_data/`
	)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch findings assessment sunburst data:', error);
			return [];
		});

	// Start all operations analytics fetches in parallel
	const detectionPromise = fetch(`${BASE_API_URL}/incidents/detection_breakdown/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch incident detection breakdown:', error);
			return { results: [] };
		});

	const monthlyPromise = fetch(`${BASE_API_URL}/incidents/monthly_metrics/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch monthly incident metrics:', error);
			return { results: { months: [], monthly_counts: [], cumulative_counts: [] } };
		});

	const summaryPromise = fetch(`${BASE_API_URL}/incidents/summary_stats/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch incident summary stats:', error);
			return { results: { total_incidents: 0, incidents_this_month: 0, open_incidents: 0 } };
		});

	const severityPromise = fetch(`${BASE_API_URL}/incidents/severity_breakdown/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch incident severity breakdown:', error);
			return { results: [] };
		});

	const qualificationsPromise = fetch(`${BASE_API_URL}/incidents/qualifications_breakdown/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch incident qualifications breakdown:', error);
			return { results: { labels: [], values: [] } };
		});

	const exceptionSankeyPromise = fetch(`${BASE_API_URL}/security-exceptions/sankey_data/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch security exception Sankey data:', error);
			return { results: { nodes: [], links: [] } };
		});

	const sunburstPromise = fetch(`${BASE_API_URL}/applied-controls/sunburst_data/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch applied controls sunburst data:', error);
			return { results: [] };
		});

	const findingsSankeyPromise = fetch(`${BASE_API_URL}/findings/sankey_data/`)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch findings Sankey data:', error);
			return { results: { nodes: [], links: [] } };
		});

	const operationsAnalyticsPromise = Promise.all([
		detectionPromise,
		monthlyPromise,
		summaryPromise,
		severityPromise,
		qualificationsPromise,
		exceptionSankeyPromise,
		sunburstPromise,
		findingsSankeyPromise
	])
		.then(
			([
				detectionData,
				monthlyData,
				summaryData,
				severityData,
				qualificationsData,
				exceptionSankeyData,
				sunburstData,
				findingsSankeyData
			]) => ({
				incident_detection_breakdown: detectionData.results,
				monthly_metrics: monthlyData.results,
				summary_stats: summaryData.results,
				severity_breakdown: severityData.results,
				qualifications_breakdown: qualificationsData.results,
				exception_sankey: exceptionSankeyData.results,
				applied_controls_sunburst: sunburstData.results,
				findings_sankey: findingsSankeyData.results
			})
		)
		.catch((error) => {
			console.error('Failed to fetch operations analytics:', error);
			return null;
		});

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
			metrics: metricsPromise,
			counters: countersPromise,
			combinedAssessmentsStatus: combinedAssessmentsStatusPromise,
			governanceCalendarData: governanceCalendarDataPromise,
			operationsAnalytics: operationsAnalyticsPromise,
			vulnerabilitySankeyData: vulnerabilitySankeyDataPromise,
			findingsAssessmentSunburstData: findingsAssessmentSunburstDataPromise
		}
	};
};
