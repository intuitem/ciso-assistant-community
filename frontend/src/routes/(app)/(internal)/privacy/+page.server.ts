import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ fetch, depends }) => {
	depends('app:privacy-dashboard');

	try {
		// Load data assets summary
		const assetsResponse = await fetch(`${base}/api/privacy/data-assets/?limit=1000`);
		const assetsData = assetsResponse.ok ? await assetsResponse.json() : { results: [], count: 0 };

		// Load consent records summary
		const consentResponse = await fetch(`${base}/api/privacy/consent-records/?limit=1000`);
		const consentData = consentResponse.ok ? await consentResponse.json() : { results: [], count: 0 };

		// Load data subject rights summary
		const rightsResponse = await fetch(`${base}/api/privacy/data-subject-rights/?limit=1000`);
		const rightsData = rightsResponse.ok ? await rightsResponse.json() : { results: [], count: 0 };

		// Calculate metrics
		const assets = assetsData.results || [];
		const consents = consentData.results || [];
		const rights = rightsData.results || [];

		const metrics = {
			totalDataAssets: assetsData.count || 0,
			compliantAssets: assets.filter((a: any) => a.compliance_status === 'compliant').length,
			nonCompliantAssets: assets.filter((a: any) => a.compliance_status === 'non_compliant').length,
			piaRequired: assets.filter((a: any) => a.pia_required && !a.pia_completed).length,

			totalConsents: consentData.count || 0,
			activeConsents: consents.filter((c: any) => c.status === 'active').length,
			withdrawnConsents: consents.filter((c: any) => c.status === 'withdrawn').length,
			expiredConsents: consents.filter((c: any) => c.status === 'expired').length,

			totalRightsRequests: rightsData.count || 0,
			completedRights: rights.filter((r: any) => r.status === 'completed').length,
			pendingRights: rights.filter((r: any) => r.status === 'processing' || r.status === 'received').length,
			rejectedRights: rights.filter((r: any) => r.status === 'rejected').length
		};

		// Calculate compliance percentages
		metrics.compliancePercentage = metrics.totalDataAssets > 0 ?
			Math.round((metrics.compliantAssets / metrics.totalDataAssets) * 100) : 0;

		metrics.consentRetentionRate = metrics.totalConsents > 0 ?
			Math.round((metrics.activeConsents / metrics.totalConsents) * 100) : 0;

		metrics.rightsFulfillmentRate = metrics.totalRightsRequests > 0 ?
			Math.round((metrics.completedRights / metrics.totalRightsRequests) * 100) : 0;

		return {
			title: 'Privacy Program Dashboard',
			metrics,
			recentAssets: assets.slice(0, 5),
			recentConsents: consents.slice(0, 5),
			recentRights: rights.slice(0, 5)
		};
	} catch (err) {
		console.error('Error loading privacy dashboard:', err);
		throw error(500, 'Failed to load privacy dashboard');
	}
};
