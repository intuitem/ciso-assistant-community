import { getModelInfo, urlParamModelSelectFields } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import { modelSchema } from '$lib/utils/schemas';
import type { PageServerLoad } from './$types';
import { type Actions, fail } from '@sveltejs/kit';
import { nestedDeleteFormAction, nestedWriteFormAction } from '$lib/utils/actions';
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

	// Calculate the first free row (after all existing widgets)
	const firstFreeRow =
		widgets.length > 0
			? Math.max(...widgets.map((w: any) => (w.position_y || 0) + (w.height || 2)))
			: 0;

	// Prepare the widget create form (shallow copy to avoid mutating shared cache)
	const widgetModel = { ...getModelInfo('dashboard-widgets') };
	const widgetSchema = modelSchema('dashboard-widgets');
	const widgetCreateForm = await superValidate(
		{
			dashboard: event.params.id,
			folder: detailData.data.folder?.id || detailData.data.folder,
			position_y: firstFreeRow
		},
		zod(widgetSchema),
		{ errors: false }
	);

	// Prepare the text widget create form (shallow copy to avoid mutating shared cache)
	const textWidgetModel = { ...getModelInfo('dashboard-text-widgets') };
	const textWidgetSchema = modelSchema('dashboard-text-widgets');
	const textWidgetCreateForm = await superValidate(
		{
			dashboard: event.params.id,
			folder: detailData.data.folder?.id || detailData.data.folder,
			position_y: firstFreeRow,
			// Set text widget specific defaults
			chart_type: 'text',
			time_range: 'all_time',
			aggregation: 'none',
			show_target: false,
			show_legend: false,
			height: 1
		},
		zod(textWidgetSchema),
		{ errors: false }
	);

	// Prepare the builtin widget create form (shallow copy to avoid mutating shared cache)
	const builtinWidgetModel = { ...getModelInfo('dashboard-builtin-widgets') };
	const builtinWidgetSchema = modelSchema('dashboard-builtin-widgets');
	const builtinWidgetCreateForm = await superValidate(
		{
			dashboard: event.params.id,
			folder: detailData.data.folder?.id || detailData.data.folder,
			position_y: firstFreeRow,
			time_range: 'all_time',
			aggregation: 'none',
			show_target: false
		},
		zod(builtinWidgetSchema),
		{ errors: false }
	);

	// Fetch selectOptions for widget form
	const selectFields = urlParamModelSelectFields('dashboard-widgets');
	const selectOptions: Record<string, any> = {};

	for (const selectField of selectFields) {
		if (selectField.detail) continue;
		const url = `${BASE_API_URL}/${widgetModel.endpointUrl}/${selectField.field}/`;
		const response = await event.fetch(url);
		if (response.ok) {
			selectOptions[selectField.field] = await response.json().then((data: Record<string, any>) =>
				Object.entries(data).map(([key, value]) => ({
					label: value,
					value: selectField.valueType === 'number' ? parseInt(key) : key
				}))
			);
		}
	}

	widgetModel.selectOptions = selectOptions;

	// Fetch supported models for builtin metrics
	const supportedModelsEndpoint = `${BASE_API_URL}/metrology/builtin-metric-samples/supported_models/`;
	const supportedModelsResponse = await event.fetch(supportedModelsEndpoint);
	const supportedModels = supportedModelsResponse.ok ? await supportedModelsResponse.json() : {};

	// Add selectOptions to builtin widget model
	builtinWidgetModel.selectOptions = selectOptions;

	return {
		...detailData,
		widgets,
		widgetModel,
		widgetCreateForm,
		textWidgetModel,
		textWidgetCreateForm,
		builtinWidgetModel,
		builtinWidgetCreateForm,
		supportedModels
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	updateWidget: async (event) => {
		return nestedWriteFormAction({ event, action: 'update' });
	},
	saveLayout: async (event) => {
		const formData = await event.request.formData();
		const widgetsJson = formData.get('widgets') as string;

		if (!widgetsJson) {
			return fail(400, { error: 'No widgets data provided' });
		}

		try {
			const widgets = JSON.parse(widgetsJson);
			const errors: string[] = [];

			for (const widget of widgets) {
				const response = await event.fetch(
					`${BASE_API_URL}/metrology/dashboard-widgets/${widget.id}/`,
					{
						method: 'PATCH',
						headers: {
							'Content-Type': 'application/json'
						},
						body: JSON.stringify({
							position_x: widget.position_x,
							position_y: widget.position_y,
							width: widget.width,
							height: widget.height
						})
					}
				);

				if (!response.ok) {
					errors.push(`Failed to update widget ${widget.id}`);
				}
			}

			if (errors.length > 0) {
				return fail(500, { error: errors.join(', ') });
			}

			return { success: true };
		} catch (e) {
			return fail(500, { error: 'Failed to parse widgets data' });
		}
	}
};
