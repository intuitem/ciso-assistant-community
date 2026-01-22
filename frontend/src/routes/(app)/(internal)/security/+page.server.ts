import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ fetch, depends }) => {
	depends('app:security-dashboard');

	try {
		// Load security incidents summary
		const incidentsResponse = await fetch(`${base}/api/security/incidents/?limit=1000`);
		const incidentsData = incidentsResponse.ok ? await incidentsResponse.json() : { results: [], count: 0 };

		// Calculate metrics
		const incidents = incidentsData.results || [];

		const metrics = {
			totalIncidents: incidentsData.count || 0,
			activeIncidents: incidents.filter((i: any) => i.status === 'active').length,
			criticalIncidents: incidents.filter((i: any) => i.severity === 'critical').length,
			highSeverityIncidents: incidents.filter((i: any) => i.severity === 'high').length,
			mediumSeverityIncidents: incidents.filter((i: any) => i.severity === 'medium').length,
			lowSeverityIncidents: incidents.filter((i: any) => i.severity === 'low').length,

			// Calculate response time metrics
			averageResponseTime: 0, // Would calculate from incident data
			openIncidents: incidents.filter((i: any) => i.status === 'open' || i.status === 'investigating').length,
			resolvedIncidents: incidents.filter((i: any) => i.status === 'resolved' || i.status === 'closed').length,

			// Calculate by category
			phishingIncidents: incidents.filter((i: any) => i.incident_type === 'phishing').length,
			malwareIncidents: incidents.filter((i: any) => i.incident_type === 'malware').length,
			unauthorizedAccess: incidents.filter((i: any) => i.incident_type === 'unauthorized_access').length,
			dataBreach: incidents.filter((i: any) => i.incident_type === 'data_breach').length,

			// Calculate SLA compliance
			slaCompliant: incidents.filter((i: any) => {
				// Simple SLA check - incidents resolved within 24 hours for high/critical
				if (['critical', 'high'].includes(i.severity)) {
					const responseTime = new Date(i.resolved_at || i.updated_at) - new Date(i.detected_at);
					return responseTime <= 24 * 60 * 60 * 1000; // 24 hours
				}
				return true;
			}).length,

			recentIncidents: incidents.slice(0, 5),
			criticalIncidentsList: incidents.filter((i: any) => i.severity === 'critical').slice(0, 5)
		};

		// Calculate percentages
		metrics.slaComplianceRate = metrics.totalIncidents > 0 ?
			Math.round((metrics.slaCompliant / metrics.totalIncidents) * 100) : 100;

		metrics.resolutionRate = metrics.totalIncidents > 0 ?
			Math.round((metrics.resolvedIncidents / metrics.totalIncidents) * 100) : 0;

		return {
			title: 'Security Operations Dashboard',
			metrics
		};
	} catch (err) {
		console.error('Error loading security dashboard:', err);
		throw error(500, 'Failed to load security dashboard');
	}
};
