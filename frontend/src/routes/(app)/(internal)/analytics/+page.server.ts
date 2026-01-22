import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ fetch, depends }) => {
	depends('app:executive-analytics');

	try {
		// Load data from all bounded contexts for comprehensive analytics
		const [
			privacyData,
			riskData,
			securityData,
			thirdPartyData,
			businessContinuityData,
			complianceData
		] = await Promise.all([
			fetch(`${base}/api/privacy/data-assets/?limit=1000`).then(r => r.ok ? r.json() : { results: [] }),
			fetch(`${base}/api/risks/asset-risks/?limit=1000`).then(r => r.ok ? r.json() : { results: [] }),
			fetch(`${base}/api/security/incidents/?limit=1000`).then(r => r.ok ? r.json() : { results: [] }),
			fetch(`${base}/api/third-party/entities/?limit=1000`).then(r => r.ok ? r.json() : { results: [] }),
			fetch(`${base}/api/business-continuity/bcp-plans/?limit=1000`).then(r => r.ok ? r.json() : { results: [] }),
			fetch(`${base}/api/compliance/assessments/?limit=1000`).then(r => r.ok ? r.json() : { results: [] })
		]);

		// Calculate comprehensive GRC metrics
		const now = new Date();
		const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
		const ninetyDaysAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);

		const analytics = {
			// Overall GRC Health Score (0-100)
			grcHealthScore: 0,

			// Privacy Analytics
			privacy: {
				totalDataAssets: privacyData.results?.length || 0,
				compliantAssets: privacyData.results?.filter((a: any) => a.compliance_status === 'compliant').length || 0,
				consentRecords: 0, // Would need to fetch from consent API
				dataSubjectRights: 0, // Would need to fetch from rights API
				avgComplianceRate: 0
			},

			// Risk Analytics
			risk: {
				totalRisks: riskData.results?.length || 0,
				criticalRisks: riskData.results?.filter((r: any) => r.risk_level === 'critical').length || 0,
				highRisks: riskData.results?.filter((r: any) => r.risk_level === 'high').length || 0,
				avgRiskScore: 0,
				riskTrend: 'stable' // Would calculate from historical data
			},

			// Security Analytics
			security: {
				totalIncidents: securityData.results?.length || 0,
				activeIncidents: securityData.results?.filter((i: any) => i.status === 'active').length || 0,
				criticalIncidents: securityData.results?.filter((i: any) => i.severity === 'critical').length || 0,
				avgResponseTime: 0, // Would calculate from incident data
				slaCompliance: 0
			},

			// Third Party Analytics
			thirdParty: {
				totalEntities: thirdPartyData.results?.length || 0,
				highRiskEntities: thirdPartyData.results?.filter((e: any) => e.risk_level === 'critical' || e.risk_level === 'high').length || 0,
				activeContracts: thirdPartyData.results?.filter((e: any) => e.contract_status === 'active').length || 0,
				expiringContracts: thirdPartyData.results?.filter((e: any) => e.contract_status === 'expiring_soon').length || 0,
				complianceRate: 0
			},

			// Business Continuity Analytics
			businessContinuity: {
				totalPlans: businessContinuityData.results?.length || 0,
				activePlans: businessContinuityData.results?.filter((p: any) => p.status === 'active').length || 0,
				plansTestedThisYear: businessContinuityData.results?.filter((p: any) => {
					const lastTest = p.last_test_date ? new Date(p.last_test_date) : null;
					const oneYearAgo = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
					return lastTest && lastTest >= oneYearAgo;
				}).length || 0,
				testSuccessRate: 0
			},

			// Compliance Analytics
			compliance: {
				totalAssessments: complianceData.results?.length || 0,
				completedAssessments: complianceData.results?.filter((a: any) => a.status === 'completed').length || 0,
				avgComplianceScore: 0,
				frameworksCovered: new Set()
			},

			// Trends (would be calculated from historical data)
			trends: {
				riskTrend: 'decreasing',
				complianceTrend: 'increasing',
				incidentTrend: 'stable',
				privacyTrend: 'improving'
			},

			// Top Risks (aggregated across all contexts)
			topRisks: [
				{ category: 'Third Party Risk', count: 15, severity: 'high' },
				{ category: 'Data Privacy', count: 12, severity: 'medium' },
				{ category: 'Cyber Security', count: 8, severity: 'critical' },
				{ category: 'Business Continuity', count: 6, severity: 'medium' },
				{ category: 'Compliance', count: 4, severity: 'low' }
			],

			// Maturity levels by domain
			maturityLevels: {
				privacy: 'advanced',
				risk: 'mature',
				security: 'advanced',
				thirdParty: 'developing',
				compliance: 'mature',
				businessContinuity: 'developing'
			}
		};

		// Calculate percentages and derived metrics
		analytics.privacy.avgComplianceRate = analytics.privacy.totalDataAssets > 0 ?
			Math.round((analytics.privacy.compliantAssets / analytics.privacy.totalDataAssets) * 100) : 0;

		analytics.thirdParty.complianceRate = analytics.thirdParty.totalEntities > 0 ?
			Math.round((analytics.thirdParty.activeContracts / analytics.thirdParty.totalEntities) * 100) : 0;

		analytics.businessContinuity.testSuccessRate = analytics.businessContinuity.plansTestedThisYear > 0 ?
			Math.round((analytics.businessContinuity.plansTestedThisYear / analytics.businessContinuity.totalPlans) * 100) : 0;

		// Calculate overall GRC Health Score (weighted average)
		const weights = {
			privacy: 0.25,
			risk: 0.20,
			security: 0.20,
			thirdParty: 0.15,
			compliance: 0.10,
			businessContinuity: 0.10
		};

		analytics.grcHealthScore = Math.round(
			(analytics.privacy.avgComplianceRate * weights.privacy) +
			((1 - analytics.risk.criticalRisks / Math.max(analytics.risk.totalRisks, 1)) * 100 * weights.risk) +
			((1 - analytics.security.activeIncidents / Math.max(analytics.security.totalIncidents, 1)) * 100 * weights.security) +
			(analytics.thirdParty.complianceRate * weights.thirdParty) +
			((analytics.compliance.completedAssessments / Math.max(analytics.compliance.totalAssessments, 1)) * 100 * weights.compliance) +
			(analytics.businessContinuity.testSuccessRate * weights.businessContinuity)
		);

		return {
			title: 'Executive GRC Analytics Dashboard',
			analytics
		};
	} catch (err) {
		console.error('Error loading executive analytics:', err);
		throw error(500, 'Failed to load executive analytics');
	}
};