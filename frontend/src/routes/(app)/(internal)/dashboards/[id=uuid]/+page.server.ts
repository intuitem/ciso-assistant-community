import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
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
	const widgetsResponse = await event.fetch(widgetsEndpoint);
	const widgetsData = widgetsResponse.ok ? await widgetsResponse.json() : { results: [] };

	// For each widget, fetch metric samples
	const widgets = widgetsData.results || [];
	const widgetsWithSamples = await Promise.all(
		widgets.map(async (widget: any) => {
			const metricInstanceId = widget.metric_instance?.id || widget.metric_instance;
			if (!metricInstanceId) return { ...widget, samples: [] };

			const samplesEndpoint = `${BASE_API_URL}/metrology/metric-samples/?metric_instance=${metricInstanceId}`;
			const samplesResponse = await event.fetch(samplesEndpoint);
			const samplesData = samplesResponse.ok ? await samplesResponse.json() : { results: [] };

			return {
				...widget,
				samples: samplesData.results || []
			};
		})
	);

	return {
		...detailData,
		widgets: widgetsWithSamples
	};
};
