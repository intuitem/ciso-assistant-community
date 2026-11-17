import { BASE_API_URL } from '#lib/utils/constants.js';
import { fetchAllPages } from '#lib/utils/pagination.js';
import type { RiskMatrix, RiskMatrixJsonDefinition } from '#lib/utils/types.js';
import type { PageServerLoad } from './$types';
import { m } from '#paraglide/messages.js';

export const load: PageServerLoad = async ({ fetch }) => {
	const req_data = await fetchAllPages<RiskMatrix>(fetch, `${BASE_API_URL}/risk-matrices/`);

	const risk_matrices: RiskMatrixJsonDefinition[] = req_data.map((risk_matrix: RiskMatrix) => ({
		...JSON.parse(risk_matrix.json_definition),
		name: risk_matrix.name
	}));

	return {
		risk_matrices,
		title: m.scoringAssistant()
	};
};
