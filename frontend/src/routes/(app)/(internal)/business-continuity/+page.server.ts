import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ fetch, depends }) => {
	depends('app:business-continuity-dashboard');

	try {
		// Load BCP plans summary
		const plansResponse = await fetch(`${base}/api/business-continuity/bcp-plans/?limit=1000`);
		const plansData = plansResponse.ok ? await plansResponse.json() : { results: [], count: 0 };

		// Calculate metrics
		const plans = plansData.results || [];

		const metrics = {
			totalPlans: plansData.count || 0,
			activePlans: plans.filter((p: any) => p.status === 'active').length,
			draftPlans: plans.filter((p: any) => p.status === 'draft').length,
			expiredPlans: plans.filter((p: any) => p.status === 'expired').length,

			// Calculate testing status
			plansNeedingTesting: plans.filter((p: any) => {
				const lastTest = p.last_test_date ? new Date(p.last_test_date) : null;
				const now = new Date();
				const oneYearAgo = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
				return !lastTest || lastTest < oneYearAgo;
			}).length,

			plansTestedThisYear: plans.filter((p: any) => {
				const lastTest = p.last_test_date ? new Date(p.last_test_date) : null;
				const now = new Date();
				const oneYearAgo = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
				return lastTest && lastTest >= oneYearAgo;
			}).length,

			// Calculate success rates
			successfulTests: plans.filter((p: any) => p.last_test_result === 'successful').length,
			failedTests: plans.filter((p: any) => p.last_test_result === 'failed').length,

			// Calculate by business impact
			highImpactPlans: plans.filter((p: any) => p.business_impact === 'high').length,
			mediumImpactPlans: plans.filter((p: any) => p.business_impact === 'medium').length,
			lowImpactPlans: plans.filter((p: any) => p.business_impact === 'low').length,

			recentPlans: plans.slice(0, 5),
			plansNeedingAttention: plans.filter((p: any) => {
				// Plans that are expired, need testing, or have failed tests
				const lastTest = p.last_test_date ? new Date(p.last_test_date) : null;
				const now = new Date();
				const oneYearAgo = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
				return p.status === 'expired' ||
					   (!lastTest || lastTest < oneYearAgo) ||
					   p.last_test_result === 'failed';
			}).slice(0, 5)
		};

		// Calculate percentages
		metrics.testSuccessRate = (metrics.successfulTests + metrics.failedTests) > 0 ?
			Math.round((metrics.successfulTests / (metrics.successfulTests + metrics.failedTests)) * 100) : 0;

		metrics.plansUpToDate = metrics.totalPlans > 0 ?
			Math.round(((metrics.totalPlans - metrics.plansNeedingTesting) / metrics.totalPlans) * 100) : 0;

		return {
			title: 'Business Continuity Management',
			metrics
		};
	} catch (err) {
		console.error('Error loading business continuity dashboard:', err);
		throw error(500, 'Failed to load business continuity dashboard');
	}
};
