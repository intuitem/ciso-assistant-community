import { BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	// Load is handled by parent layout
	return {};
};

export const actions: Actions = {
	default: async ({ request, fetch, params }) => {
		const formData = await request.formData();
		const data = JSON.parse(formData.get('data') as string);

		try {
			const response = await fetch(
				`${BASE_API_URL}/risk-assessments/${params.id}/convert_to_quantitative/`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(data)
				}
			);

			if (!response.ok) {
				const error = await response.json();
				return fail(response.status, {
					error: error.detail || 'Conversion failed',
					data
				});
			}

			const result = await response.json();

			// Return the result with the new study ID for client-side redirect
			return {
				success: true,
				quantitative_risk_study_id: result.quantitative_risk_study_id,
				scenarios_converted: result.scenarios_converted,
				scenarios_skipped: result.scenarios_skipped,
				message: result.message
			};
		} catch (error) {
			console.error('Conversion error:', error);
			return fail(500, {
				error: 'An unexpected error occurred during conversion',
				data
			});
		}
	}
};
