import { BASE_API_URL } from '#lib/utils/constants.js';
import { fetchAllPages } from '#lib/utils/pagination.js';
import type { PageServerLoad } from './$types';

// Frameworks the pre-read has guidance for (backend/core/audit_guidance).
const SUPPORTED_URNS = ['urn:intuitem:risk:framework:iso27001-2022'];

export const load: PageServerLoad = async ({ fetch }) => {
	const frameworks = (
		await fetchAllPages<any>(fetch, `${BASE_API_URL}/frameworks/?fields=urn`)
	).filter((f) => SUPPORTED_URNS.includes(f.urn));
	const audits = (
		await Promise.all(
			frameworks.map((f) =>
				fetchAllPages<any>(
					fetch,
					`${BASE_API_URL}/compliance-assessments/?framework=${f.id}&fields=name,folder,perimeter,status`
				)
			)
		)
	).flat();
	return { frameworks, audits, title: 'Auditor pre-read' };
};
