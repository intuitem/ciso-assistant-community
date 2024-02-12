export const navData = {
	items: [
		// {
		// 	name: 'Home',
		// 	items: [
		// 		{
		// 			name: 'Home',
		// 			fa_icon: 'fa-solid fa-house',
		// 			href: '/'
		// 		},
		// 		{ name: 'Quick start', fa_icon: 'fa-solid fa-plane', href: '/quick-start' }
		// 	]
		// },
		{
			name: 'Overview',
			items: [
				{
					name: 'Analytics',
					fa_icon: 'fa-solid fa-gauge',
					href: '/analytics',
					permissions: [
						'view_project',
						'view_riskscenario',
						'view_securityfunction',
						'view_assessment',
						'view_riskassessment'
					]
				},
				{
					name: 'Calendar',
					fa_icon: 'fa-solid fa-calendar-days',
					href: '/calendar',
					permissions: ['view_event']
				}
			]
		},
		{
			name: 'Context',
			items: [
				{
					name: 'Threats',
					fa_icon: 'fa-solid fa-biohazard',
					href: '/threats'
				},
				{
					name: 'Security functions',
					fa_icon: 'fa-solid fa-gears',
					href: '/security-functions'
				},
				{
					name: 'Security measures',
					fa_icon: 'fa-solid fa-fire-extinguisher',
					href: '/security-measures'
				},
				{
					name: 'Assets',
					fa_icon: 'fa-solid fa-gem',
					href: '/assets'
				}
			]
		},
		{
			name: 'Governance',
			items: [
				{
					name: 'Policies',
					fa_icon: 'fa-solid fa-user',
					href: '/security-measures'
				},
				{
					name: 'Risk matrices',
					fa_icon: 'fa-solid fa-table-cells-large',
					href: '/risk-matrices'
				}
			]
		},
		{
			name: 'Risk',
			items: [
				{
					name: 'Risk assessments',
					fa_icon: 'fa-solid fa-magnifying-glass-chart',
					href: '/risk-assessments'
				},
				{
					name: 'Risk scenarios',
					fa_icon: 'fa-solid fa-clone',
					href: '/risk-scenarios'
				},
				{
					name: 'Risk acceptances',
					fa_icon: 'fa-solid fa-user-tie',
					href: '/risk-acceptances'
				}
			]
		},

		{
			name: 'Compliance',
			items: [
				{
					name: 'Compliance assessments',
					fa_icon: 'fa-solid fa-arrows-to-eye',
					href: '/compliance-assessments'
				},
				{
					name: 'Evidences',
					fa_icon: 'fa-solid fa-file',
					href: '/evidences'
				},
				{
					name: 'Frameworks',
					fa_icon: 'fa-solid fa-folder',
					href: '/frameworks'
				}
			]
		},
		{
			name: 'Organisation',
			items: [
				{
					name: 'Domains',
					fa_icon: 'fa-solid fa-diagram-project',
					href: '/folders'
				},
				{
					name: 'Projects',
					fa_icon: 'fa-solid fa-cubes',
					href: '/projects'
				},
				{
					name: 'Users',
					fa_icon: 'fa-solid fa-user',
					href: '/users'
				},
				{
					name: 'User groups',
					fa_icon: 'fa-solid fa-users',
					href: '/user-groups'
				},
				{
					name: 'Role assignments',
					fa_icon: 'fa-solid fa-user-tag',
					href: '/role-assignments'
				}
			]
		},

		{
			name: 'Extra',
			items: [
				{
					name: 'X-Rays',
					fa_icon: 'fa-solid fa-bolt',
					href: '/x-rays',
					permissions: ['view_riskassessment', 'view_assessment']
				},
				{
					name: 'Scoring assistant',
					fa_icon: 'fa-solid fa-star-half-stroke',
					href: '/scoring-assistant',
					permissions: ['view_riskmatrix']
				},
				{
					name: 'Libraries',
					fa_icon: 'fa-solid fa-folder-plus',
					href: '/libraries',
					permissions: ['add_threat', 'add_riskmatrix', 'add_securityfunction', 'add_framework']
				},
				{
					name: 'Backup & restore',
					fa_icon: 'fa-solid fa-floppy-disk',
					href: '/backup-restore',
					permissions: ['backup']
				}
				// {
				// 	name: 'License management',
				// 	fa_icon: 'fa-solid fa-file-invoice',
				// 	href: '/license-management'
				// }
			]
		}
	]
};
