import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import { modelSchema } from '$lib/utils/schemas';
import type { PageServerLoad } from './$types';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

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

	const widgets = widgetsData.results || [];

	// Fetch samples for each widget based on time range
	const widgetsWithSamples = await Promise.all(
		widgets.map(async (widget: any) => {
			const samplesEndpoint = `${BASE_API_URL}/metrology/metric-samples/?metric_instance=${widget.metric_instance.id}`;
			const samplesResponse = await event.fetch(samplesEndpoint);
			const samplesData = samplesResponse.ok ? await samplesResponse.json() : { results: [] };
			return {
				...widget,
				samples: samplesData.results || []
			};
		})
	);

	// Prepare the widget create form
	const widgetModel = getModelInfo('dashboard-widgets');
	const widgetSchema = modelSchema('dashboard-widgets');
	const widgetCreateForm = await superValidate(
		{
			dashboard: event.params.id,
			folder: detailData.data.folder?.id || detailData.data.folder
		},
		zod(widgetSchema),
		{ errors: false }
	);

	return {
		...detailData,
		widgets: widgetsWithSamples,
		widgetModel,
		widgetCreateForm
	};
};
