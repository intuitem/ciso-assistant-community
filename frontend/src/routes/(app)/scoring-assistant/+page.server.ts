import { BASE_API_URL } from '$lib/utils/constants';
import type { RiskMatrix, RiskMatrixJsonDefinition } from '$lib/utils/types';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch }) => {
	const req = await fetch(`${BASE_API_URL}/risk-matrices/`);
	const req_data = await req.json();

	const risk_matrices: RiskMatrixJsonDefinition[] = req_data.results.map(
		(risk_matrix: RiskMatrix) => ({
			...JSON.parse(risk_matrix.json_definition),
			name: risk_matrix.name
		})
	);

	if (!risk_matrices.length) {
		error(400, 'You must import at least one risk matrix to access this page !');
	}

	return {
		risk_matrices
	};
};
