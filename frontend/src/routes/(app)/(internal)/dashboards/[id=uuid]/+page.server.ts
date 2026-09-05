import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	event.depends('dashboard:widgets');

	const detailData = await loadDetail({
		event,
		model: getModelInfo('dashboards'),
		id: event.params.id
	});

	// Fetch widgets for this dashboard
	const widgetsEndpoint = `${BASE_API_URL}/metrology/dashboard-widgets/?dashboard=${event.params.id}`;
	const widgets = await fetchAllPages(event.fetch, widgetsEndpoint).catch(() => []);

	// For each widget, fetch samples (either custom or builtin)
	const widgetsWithSamples = await Promise.all(
		widgets.map(async (widget: any) => {
			// Check if this is a builtin metric widget
			const isBuiltinMetric = widget.is_builtin_metric || widget.target_content_type;

			if (isBuiltinMetric) {
				// Fetch builtin metric samples for the target object
				const targetContentType = widget.target_content_type;
				const targetObjectId = widget.target_object_id;

				if (!targetContentType || !targetObjectId) {
					return { ...widget, samples: [], builtinSamples: [] };
				}

				const builtinSamplesEndpoint = `${BASE_API_URL}/metrology/builtin-metric-samples/for_object/?content_type_id=${targetContentType}&object_id=${targetObjectId}`;
				const builtinSamplesResponse = await event.fetch(builtinSamplesEndpoint);
				const builtinSamplesData = builtinSamplesResponse.ok
					? await builtinSamplesResponse.json()
					: [];

				return {
					...widget,
					samples: [],
					builtinSamples: Array.isArray(builtinSamplesData) ? builtinSamplesData : []
				};
			} else {
				// Fetch custom metric samples
				const metricInstanceId = widget.metric_instance?.id || widget.metric_instance;
				if (!metricInstanceId) return { ...widget, samples: [], builtinSamples: [] };

				const samplesEndpoint = `${BASE_API_URL}/metrology/custom-metric-samples/?metric_instance=${metricInstanceId}`;
				const samples = await fetchAllPages(event.fetch, samplesEndpoint).catch(() => []);

				return {
					...widget,
					samples,
					builtinSamples: []
				};
			}
		})
	);

	return {
		...detailData,
		widgets: widgetsWithSamples
	};
};
