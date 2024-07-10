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
			name: 'overview',
			items: [
				{
					name: 'analytics',
					fa_icon: 'fa-solid fa-gauge',
					href: '/analytics',
					permissions: [
						'view_project',
						'view_riskscenario',
						'view_referencecontrol',
						'view_assessment',
						'view_riskassessment'
					]
				},
				{
					name: 'calendar',
					fa_icon: 'fa-solid fa-calendar-days',
					href: '/calendar',
					permissions: [
						'view_appliedcontrol',
						'view_riskacceptance',
						'view_riskassessment',
						'view_complianceassessment'
					]
				}
			]
		},
		{
			name: 'context',
			items: [
				{
					name: 'threats',
					fa_icon: 'fa-solid fa-biohazard',
					href: '/threats'
				},
				{
					name: 'referenceControls',
					fa_icon: 'fa-solid fa-gears',
					href: '/reference-controls'
				},
				{
					name: 'appliedControls',
					fa_icon: 'fa-solid fa-fire-extinguisher',
					href: '/applied-controls'
				},
				{
					name: 'assets',
					fa_icon: 'fa-solid fa-gem',
					href: '/assets'
				}
			]
		},
		{
			name: 'governance',
			items: [
				{
					name: 'policies',
					fa_icon: 'fa-solid fa-user',
					href: '/policies',
					permissions: ['view_appliedcontrol']
				},
				{
					name: 'riskMatrices',
					fa_icon: 'fa-solid fa-table-cells-large',
					href: '/risk-matrices'
				}
			]
		},
		{
			name: 'risk',
			items: [
				{
					name: 'riskAssessments',
					fa_icon: 'fa-solid fa-magnifying-glass-chart',
					href: '/risk-assessments'
				},
				{
					name: 'riskScenarios',
					fa_icon: 'fa-solid fa-clone',
					href: '/risk-scenarios'
				},
				{
					name: 'riskAcceptances',
					fa_icon: 'fa-solid fa-user-tie',
					href: '/risk-acceptances'
				}
			]
		},

		{
			name: 'compliance',
			items: [
				{
					name: 'complianceAssessments',
					fa_icon: 'fa-solid fa-arrows-to-eye',
					href: '/compliance-assessments'
				},
				{
					name: 'evidences',
					fa_icon: 'fa-solid fa-file',
					href: '/evidences'
				},
				{
					name: 'frameworks',
					fa_icon: 'fa-solid fa-folder',
					href: '/frameworks'
				},
				{
					name: 'requirementMappingSets',
					fa_icon: 'fa-solid fa-diagram-project',
					href: '/requirement-mapping-sets'
				}
			]
		},
		{
			name: 'organization',
			items: [
				{
					name: 'domains',
					fa_icon: 'fa-solid fa-sitemap',
					href: '/folders'
				},
				{
					name: 'projects',
					fa_icon: 'fa-solid fa-cubes',
					href: '/projects'
				},
				{
					name: 'users',
					fa_icon: 'fa-solid fa-user',
					href: '/users'
				},
				{
					name: 'userGroups',
					fa_icon: 'fa-solid fa-users',
					href: '/user-groups'
				},
				{
					name: 'roleAssignments',
					fa_icon: 'fa-solid fa-user-tag',
					href: '/role-assignments'
				}
			]
		},
		{
			name: 'extra',
			items: [
				{
					name: 'xRays',
					fa_icon: 'fa-solid fa-bolt',
					href: '/x-rays',
					permissions: ['view_riskassessment', 'view_assessment']
				},
				{
					name: 'scoringAssistant',
					fa_icon: 'fa-solid fa-star-half-stroke',
					href: '/scoring-assistant',
					permissions: ['view_riskmatrix']
				},
				{
					name: 'libraries',
					fa_icon: 'fa-solid fa-folder-plus',
					href: '/libraries',
					permissions: ['add_threat', 'add_riskmatrix', 'add_referencecontrol', 'add_framework']
				},
				{
					name: 'backupRestore',
					fa_icon: 'fa-solid fa-floppy-disk',
					href: '/backup-restore',
					permissions: ['backup']
				},
				{
					name: 'settings',
					fa_icon: 'fa-solid fa-cog',
					href: '/settings',
					permissions: ['change_globalsettings']
				}
			]
		},
		{
			name: 'advanced',
			items: [
				{
					name: 'requirementAssessments',
					fa_icon: 'fa-solid fa-cogs',
					href: '/requirement-assessments'
				}
			]
		}
	]
};
