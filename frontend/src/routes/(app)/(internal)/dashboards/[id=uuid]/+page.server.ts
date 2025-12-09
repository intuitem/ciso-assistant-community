import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import { modelSchema } from '$lib/utils/schemas';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction, nestedWriteFormAction } from '$lib/utils/actions';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

export const load: PageServerLoad = async (event) => {
	// Add dependency for cache invalidation
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

	// Prepare the widget create form with initial data
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

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	}
};
