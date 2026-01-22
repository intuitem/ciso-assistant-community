import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ fetch, depends }) => {
	depends('app:third-party-dashboard');

	try {
		// Load third party entities summary
		const entitiesResponse = await fetch(`${base}/api/third-party/entities/?limit=1000`);
		const entitiesData = entitiesResponse.ok ? await entitiesResponse.json() : { results: [], count: 0 };

		// Calculate metrics
		const entities = entitiesData.results || [];

		const metrics = {
			totalEntities: entitiesData.count || 0,
			activeEntities: entities.filter((e: any) => e.status === 'active').length,
			criticalRiskEntities: entities.filter((e: any) => e.risk_level === 'critical').length,
			highRiskEntities: entities.filter((e: any) => e.risk_level === 'high').length,
			mediumRiskEntities: entities.filter((e: any) => e.risk_level === 'medium').length,
			lowRiskEntities: entities.filter((e: any) => e.risk_level === 'low').length,

			// Calculate by type
			vendors: entities.filter((e: any) => e.entity_type === 'vendor').length,
			contractors: entities.filter((e: any) => e.entity_type === 'contractor').length,
			partners: entities.filter((e: any) => e.entity_type === 'partner').length,
			suppliers: entities.filter((e: any) => e.entity_type === 'supplier').length,

			// Calculate compliance status
			compliantEntities: entities.filter((e: any) => e.compliance_status === 'compliant').length,
			nonCompliantEntities: entities.filter((e: any) => e.compliance_status === 'non_compliant').length,
			underReviewEntities: entities.filter((e: any) => e.compliance_status === 'under_review').length,

			// Calculate contract status
			activeContracts: entities.filter((e: any) => e.contract_status === 'active').length,
			expiringContracts: entities.filter((e: any) => e.contract_status === 'expiring_soon').length,
			expiredContracts: entities.filter((e: any) => e.contract_status === 'expired').length,

			recentEntities: entities.slice(0, 5),
			criticalRiskEntitiesList: entities.filter((e: any) => e.risk_level === 'critical').slice(0, 5),
			expiringContractsList: entities.filter((e: any) => e.contract_status === 'expiring_soon').slice(0, 5)
		};

		// Calculate percentages
		metrics.complianceRate = metrics.totalEntities > 0 ?
			Math.round((metrics.compliantEntities / metrics.totalEntities) * 100) : 0;

		metrics.contractHealth = metrics.totalEntities > 0 ?
			Math.round((metrics.activeContracts / metrics.totalEntities) * 100) : 0;

		metrics.overallRiskLevel = metrics.totalEntities > 0 ?
			Math.round((metrics.criticalRiskEntities + metrics.highRiskEntities) / metrics.totalEntities * 100) : 0;

		return {
			title: 'Third Party Risk Management',
			metrics
		};
	} catch (err) {
		console.error('Error loading third party dashboard:', err);
		throw error(500, 'Failed to load third party dashboard');
	}
};
