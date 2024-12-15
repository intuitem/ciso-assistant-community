import * as m from '$paraglide/messages';

export interface NavigationLink {
	label: string;
	href: string;
}

export const navigationLinks: NavigationLink[] = [
	{
		label: 'analytics',
		href: '/'
	},
	{
		label: 'myAssignments',
		href: '/my-assignments'
	},
	{
		label: 'domains',
		href: '/folders'
	},
	{
		label: 'assets',
		href: '/assets'
	},
	{
		label: 'complianceAssessments',
		href: '/compliance-assessments'
	},
	{
		label: 'riskAssessments',
		href: '/risk-assessments'
	},
	{
		label: 'riskScenarios',
		href: '/risk-scenarios'
	},
	{
		label: 'actionPlan',
		href: '/applied-controls'
	},
	{
		label: 'evidences',
		href: '/evidences'
	},
	{
		label: 'xRays',
		href: '/x-rays'
	},
	{
		label: 'libraries',
		href: '/libraries'
	},
	{
		label: 'myProfile',
		href: '/my-profile'
	},
	{
		label: 'settings',
		href: '/settings'
	}
];
