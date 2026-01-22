import { base } from '$app/paths';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { safeTranslate } from '$lib/utils/i18n';

export const load: PageServerLoad = async ({ fetch, depends }) => {
	depends('app:compliance-analytics');

	try {
		// Load compliance assessment data
		const assessmentsResponse = await fetch(`${base}/api/compliance/assessments/?limit=1000`);
		const assessmentsData = assessmentsResponse.ok ? await assessmentsData.json() : { results: [] };

		const assessments = assessmentsData.results || [];

		// Calculate compliance analytics
		const analytics = {
			totalAssessments: assessmentsData.count || 0,
			completedAssessments: assessments.filter((a: any) => a.status === 'completed').length,
			inProgressAssessments: assessments.filter((a: any) => a.status === 'in_progress').length,
			plannedAssessments: assessments.filter((a: any) => a.status === 'planned').length,

			// Framework distribution
			frameworkStats: {} as Record<string, any>,
			complianceScores: [] as number[],
			avgComplianceScore: 0,

			// Assessment results by status
			findingsCount: assessments.reduce((sum: number, a: any) => sum + (a.findings_count || 0), 0),
			exceptionsCount: assessments.reduce((sum: number, a: any) => sum + (a.exceptions_count || 0), 0),

			// Recent assessments
			recentAssessments: assessments.slice(0, 10),

			// Compliance trends
			complianceByFramework: [] as Array<{framework: string, score: number, assessments: number, status: string}>,

			// Risk-based compliance
			highRiskFrameworks: [] as string[],
			compliantFrameworks: [] as string[],
			nonCompliantFrameworks: [] as string[]
		};

		// Process framework statistics
		const frameworkMap = new Map<string, {count: number, scores: number[], completed: number}>();

		assessments.forEach((assessment: any) => {
			const framework = assessment.primary_framework || 'Unknown';
			if (!frameworkMap.has(framework)) {
				frameworkMap.set(framework, { count: 0, scores: [], completed: 0 });
			}
			const stats = frameworkMap.get(framework)!;
			stats.count++;
			if (assessment.status === 'completed' && assessment.overall_compliance_score) {
				stats.scores.push(assessment.overall_compliance_score);
				stats.completed++;
			}
		});

		// Calculate framework analytics
		frameworkMap.forEach((stats, framework) => {
			const avgScore = stats.scores.length > 0 ?
				Math.round(stats.scores.reduce((a, b) => a + b, 0) / stats.scores.length) : 0;

			analytics.frameworkStats[framework] = {
				totalAssessments: stats.count,
				completedAssessments: stats.completed,
				averageScore: avgScore,
				compliance: avgScore >= 80 ? 'compliant' :
						   avgScore >= 60 ? 'partial' : 'non-compliant'
			};

			analytics.complianceByFramework.push({
				framework,
				score: avgScore,
				assessments: stats.count,
				status: avgScore >= 80 ? 'compliant' :
					   avgScore >= 60 ? 'partial' : 'non-compliant'
			});

			if (avgScore >= 80) {
				analytics.compliantFrameworks.push(framework);
			} else if (avgScore < 60) {
				analytics.nonCompliantFrameworks.push(framework);
			}

			// Consider high-risk if score < 70
			if (avgScore < 70) {
				analytics.highRiskFrameworks.push(framework);
			}
		});

		// Calculate overall compliance score
		const completedScores = assessments
			.filter((a: any) => a.status === 'completed' && a.overall_compliance_score)
			.map((a: any) => a.overall_compliance_score);

		analytics.avgComplianceScore = completedScores.length > 0 ?
			Math.round(completedScores.reduce((a, b) => a + b, 0) / completedScores.length) : 0;

		analytics.complianceScores = completedScores;

		return {
			title: 'Compliance Analytics Dashboard',
			analytics
		};
	} catch (err) {
		console.error('Error loading compliance analytics:', err);
		throw error(500, 'Failed to load compliance analytics');
	}
};
