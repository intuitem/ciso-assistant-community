import { BASE_API_URL } from '$lib/utils/constants';
import type { Actions, PageServerLoad } from './$types';
import { fail } from '@sveltejs/kit';
import { m } from '$paraglide/messages';

async function loadCustomDashboard(fetch: typeof globalThis.fetch, dashboardId: string) {
	// Fetch the dashboard metadata
	const dashboardRes = await fetch(`${BASE_API_URL}/metrology/dashboards/${dashboardId}/`);
	if (!dashboardRes.ok) return null;
	const dashboard = await dashboardRes.json();

	// Fetch widgets for this dashboard
	const widgetsRes = await fetch(
		`${BASE_API_URL}/metrology/dashboard-widgets/?dashboard=${dashboardId}`
	);
	const widgetsData = widgetsRes.ok ? await widgetsRes.json() : { results: [] };
	const widgets = widgetsData.results || [];

	// For each widget, fetch its samples (matches /dashboards/[id]/+page.server.ts)
	const widgetsWithSamples = await Promise.all(
		widgets.map(async (widget: any) => {
			const isBuiltinMetric = widget.is_builtin_metric || widget.target_content_type;
			if (isBuiltinMetric) {
				const targetContentType = widget.target_content_type;
				const targetObjectId = widget.target_object_id;
				if (!targetContentType || !targetObjectId) {
					return { ...widget, samples: [], builtinSamples: [] };
				}
				const r = await fetch(
					`${BASE_API_URL}/metrology/builtin-metric-samples/for_object/?content_type_id=${targetContentType}&object_id=${targetObjectId}`
				);
				const data = r.ok ? await r.json() : [];
				return {
					...widget,
					samples: [],
					builtinSamples: Array.isArray(data) ? data : []
				};
			}
			const metricInstanceId = widget.metric_instance?.id || widget.metric_instance;
			if (!metricInstanceId) return { ...widget, samples: [], builtinSamples: [] };
			const r = await fetch(
				`${BASE_API_URL}/metrology/custom-metric-samples/?metric_instance=${metricInstanceId}`
			);
			const data = r.ok ? await r.json() : { results: [] };
			return { ...widget, samples: data.results || [], builtinSamples: [] };
		})
	);

	return { ...dashboard, widgets: widgetsWithSamples };
}

export const load: PageServerLoad = async ({ locals, fetch, url }) => {
	const currentYear = new Date().getFullYear();

	// All data is streamed — nothing blocks the initial page render.

	function assertOk(res: Response) {
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		return res;
	}

	const appliedControlStatusPromise = fetch(`${BASE_API_URL}/applied-controls/per_status/`)
		.then(assertOk)
		.then((res) => res.json())
		.then((res) => res.results)
		.catch(() => null);

	const taskTemplateStatusPromise = fetch(`${BASE_API_URL}/task-templates/per_status/`)
		.then(assertOk)
		.then((res) => res.json())
		.then((res) => res.results)
		.catch(() => null);

	const risksCountPerLevelPromise = fetch(`${BASE_API_URL}/risk-scenarios/count_per_level/`)
		.then(assertOk)
		.then((res) => res.json())
		.then((res) => res.results)
		.catch(() => ({ current: [], residual: [] }));

	const threatsCountPromise = fetch(`${BASE_API_URL}/threats/threats_count/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch(() => ({ results: { labels: [], values: [] } }));

	const qualificationsCountPromise = fetch(`${BASE_API_URL}/risk-scenarios/qualifications_count/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch(() => ({ results: { labels: [], values: [] } }));

	const complianceAnalyticsPromise = fetch(`${BASE_API_URL}/compliance-assessments/analytics/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch(() => ({}));

	const metricsPromise = fetch(`${BASE_API_URL}/get_metrics/`)
		.then(assertOk)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('Failed to fetch or parse metrics:', error);
			return null;
		});

	const auditsMetricsPromise = fetch(`${BASE_API_URL}/get_audits_metrics/`)
		.then(assertOk)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('Failed to fetch or parse audits metrics:', error);
			return null;
		});

	const countersPromise = fetch(`${BASE_API_URL}/get_counters/`)
		.then(assertOk)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('failed to fetch or parse counters:', error);
			return null;
		});

	const combinedAssessmentsStatusPromise = fetch(`${BASE_API_URL}/get_combined_assessments_status/`)
		.then(assertOk)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('failed to fetch or parse combined assessments status:', error);
			return null;
		});

	const governanceCalendarDataPromise = fetch(
		`${BASE_API_URL}/get_governance_calendar_data/?year=${currentYear}`
	)
		.then(assertOk)
		.then((res) => res.json())
		.then((data) => data.results)
		.catch((error) => {
			console.error('Failed to fetch governance calendar data:', error);
			return [];
		});

	const vulnerabilitySankeyDataPromise = fetch(`${BASE_API_URL}/vulnerabilities/sankey_data/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch vulnerability sankey data:', error);
			return [];
		});

	const findingsAssessmentSunburstDataPromise = fetch(
		`${BASE_API_URL}/findings-assessments/sunburst_data/`
	)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch findings assessment sunburst data:', error);
			return [];
		});

	// Start all operations analytics fetches in parallel
	const detectionPromise = fetch(`${BASE_API_URL}/incidents/detection_breakdown/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch incident detection breakdown:', error);
			return { results: [] };
		});

	const monthlyPromise = fetch(`${BASE_API_URL}/incidents/monthly_metrics/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch monthly incident metrics:', error);
			return { results: { months: [], monthly_counts: [], cumulative_counts: [] } };
		});

	const summaryPromise = fetch(`${BASE_API_URL}/incidents/summary_stats/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch incident summary stats:', error);
			return { results: { total_incidents: 0, incidents_this_month: 0, open_incidents: 0 } };
		});

	const severityPromise = fetch(`${BASE_API_URL}/incidents/severity_breakdown/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch incident severity breakdown:', error);
			return { results: [] };
		});

	const qualificationsPromise = fetch(`${BASE_API_URL}/incidents/qualifications_breakdown/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch incident qualifications breakdown:', error);
			return { results: { labels: [], values: [] } };
		});

	const exceptionSankeyPromise = fetch(`${BASE_API_URL}/security-exceptions/sankey_data/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch security exception Sankey data:', error);
			return { results: { nodes: [], links: [] } };
		});

	const sunburstPromise = fetch(`${BASE_API_URL}/applied-controls/sunburst_data/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch applied controls sunburst data:', error);
			return { results: [] };
		});

	const findingsSankeyPromise = fetch(`${BASE_API_URL}/findings/sankey_data/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch((error) => {
			console.error('Failed to fetch findings Sankey data:', error);
			return { results: { nodes: [], links: [] } };
		});

	// Custom tab: list of dashboards (always) + selected dashboard data (if any)
	const dashboardsListPromise = fetch(`${BASE_API_URL}/metrology/dashboards/`)
		.then(assertOk)
		.then((res) => res.json())
		.then((data) => data.results || [])
		.catch(() => []);

	const generalSettingsPromise = fetch(`${BASE_API_URL}/settings/general/object/`)
		.then(assertOk)
		.then((res) => res.json())
		.catch(() => ({}));

	// Resolve which dashboard to render: ?dashboard=ID > instance default global setting > none
	const customDashboardPromise = (async () => {
		const queryParamId = url.searchParams.get('dashboard');
		let dashboardId: string | null = queryParamId;
		if (!dashboardId) {
			const settings = await generalSettingsPromise;
			dashboardId = settings?.default_custom_analytics_dashboard || null;
		}
		if (!dashboardId) return null;
		try {
			return await loadCustomDashboard(fetch, dashboardId);
		} catch {
			return null;
		}
	})();

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
		user: locals.user,
		title: m.analytics(),
		stream: {
			metrics: metricsPromise,
			auditsMetrics: auditsMetricsPromise,
			counters: countersPromise,
			combinedAssessmentsStatus: combinedAssessmentsStatusPromise,
			governanceCalendarData: governanceCalendarDataPromise,
			operationsAnalytics: operationsAnalyticsPromise,
			vulnerabilitySankeyData: vulnerabilitySankeyDataPromise,
			findingsAssessmentSunburstData: findingsAssessmentSunburstDataPromise,
			appliedControlStatus: appliedControlStatusPromise,
			taskTemplateStatus: taskTemplateStatusPromise,
			risksCountPerLevel: risksCountPerLevelPromise,
			threatsCount: threatsCountPromise,
			qualificationsCount: qualificationsCountPromise,
			complianceAnalytics: complianceAnalyticsPromise,
			dashboardsList: dashboardsListPromise,
			customDashboard: customDashboardPromise
		}
	};
};

export const actions: Actions = {
	setDefaultDashboard: async ({ request, fetch }) => {
		const formData = await request.formData();
		const dashboardId = (formData.get('dashboard_id') as string) || '';
		const res = await fetch(`${BASE_API_URL}/settings/general/set-default-dashboard/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ dashboard_id: dashboardId })
		});
		if (!res.ok) {
			let detail = 'Failed to update default dashboard';
			try {
				const body = await res.json();
				detail = body.error || detail;
			} catch {
				/* ignore */
			}
			return fail(res.status, { error: detail });
		}
		return { success: true };
	}
};
