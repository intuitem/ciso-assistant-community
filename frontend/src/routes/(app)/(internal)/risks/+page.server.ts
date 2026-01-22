import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ fetch, depends }) => {
	depends('app:risk-dashboard');

	try {
		// Load asset risks summary
		const risksResponse = await fetch(`${base}/api/risks/asset-risks/?limit=1000`);
		const risksData = risksResponse.ok ? await risksData.json() : { results: [], count: 0 };

		// Load risk registers summary
		const registersResponse = await fetch(`${base}/api/risks/risk-registers/?limit=1000`);
		const registersData = registersResponse.ok ? await registersResponse.json() : { results: [], count: 0 };

		// Calculate metrics
		const risks = risksData.results || [];
		const registers = registersData.results || [];

		const metrics = {
			totalAssetRisks: risksData.count || 0,
			criticalRisks: risks.filter((r: any) => r.risk_level === 'critical').length,
			highRisks: risks.filter((r: any) => r.risk_level === 'high').length,
			mediumRisks: risks.filter((r: any) => r.risk_level === 'medium').length,
			lowRisks: risks.filter((r: any) => r.risk_level === 'low').length,

			totalRiskRegisters: registersData.count || 0,
			activeRegisters: registers.filter((r: any) => r.status === 'active').length,

			// Calculate risk score distribution
			riskScoreDistribution: {
				very_high: risks.filter((r: any) => r.calculated_risk_score >= 8).length,
				high: risks.filter((r: any) => r.calculated_risk_score >= 6 && r.calculated_risk_score < 8).length,
				medium: risks.filter((r: any) => r.calculated_risk_score >= 4 && r.calculated_risk_score < 6).length,
				low: risks.filter((r: any) => r.calculated_risk_score >= 2 && r.calculated_risk_score < 4).length,
				very_low: risks.filter((r: any) => r.calculated_risk_score < 2).length
			}
		};

		// Calculate percentages
		metrics.overallRiskLevel = metrics.totalAssetRisks > 0 ?
			Math.round((metrics.criticalRisks + metrics.highRisks) / metrics.totalAssetRisks * 100) : 0;

		return {
			title: 'Risk Management Dashboard',
			metrics,
			recentRisks: risks.slice(0, 5),
			riskRegisters: registers.slice(0, 5)
		};
	} catch (err) {
		console.error('Error loading risk dashboard:', err);
		throw error(500, 'Failed to load risk dashboard');
	}
};
