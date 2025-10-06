import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async ({ params, fetch, parent }) => {
	const endpoint = `${BASE_API_URL}/ebios-rm/studies/${params.id}/report-data/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	const interface_settings = await fetch(`${BASE_API_URL}/settings/general/object`).then((res) =>
		res.json()
	);

	// Get featureflags from parent layout
	const { featureflags } = await parent();

	return {
		reportData: data,
		useBubbles: interface_settings.interface_agg_scenario_matrix,
		inherentRiskEnabled: featureflags?.inherent_risk || false
	};
};

export const actions: Actions = {
	exportPdf: async ({ params, fetch, request }) => {
		const formData = await request.formData();
		const chartsData = formData.get('charts');

		const endpoint = `${BASE_API_URL}/ebios-rm/studies/${params.id}/report_pdf/`;

		const res = await fetch(endpoint, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: chartsData as string
		});

		if (!res.ok) {
			const errorText = await res.text();
			throw new Error(`PDF generation failed: ${errorText}`);
		}

		const pdfBlob = await res.blob();
		const buffer = await pdfBlob.arrayBuffer();

		return {
			success: true,
			pdf: Array.from(new Uint8Array(buffer))
		};
	}
};
