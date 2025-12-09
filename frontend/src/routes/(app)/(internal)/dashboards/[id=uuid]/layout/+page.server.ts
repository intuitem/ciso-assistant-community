import { getModelInfo } from '$lib/utils/crud';
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
		widgets,
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
