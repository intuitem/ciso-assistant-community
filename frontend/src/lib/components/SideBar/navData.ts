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
			name: 'dashboard',
			items: [
				{
					name: 'birdEye',
					fa_icon: 'fa-solid fa-gauge',
					href: '/bird-eye',
					permissions: [
						'view_project',
						'view_riskscenario',
						'view_referencecontrol',
						'view_assessment',
						'view_riskassessment'
					]
				},
				{
					name: 'schedules',
					fa_icon: 'fa-solid fa-calendar-days',
					href: '/schedules',
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
			name: 'repository',
			items: [
				{
					name: 'frameworks',
					fa_icon: 'fa-solid fa-folder',
					href: '/frameworks'
				},
				{
					name: 'riskMatrices',
					fa_icon: 'fa-solid fa-table-cells-large',
					href: '/risk-matrices'
				},
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
					name: 'evidences',
					fa_icon: 'fa-solid fa-file',
					href: '/evidences'
				},
				{
					name: 'appliedControls',
					fa_icon: 'fa-solid fa-fire-extinguisher',
					href: '/applied-controls'
				},
				{
					name: 'mappedControls',
					fa_icon: 'fa-solid fa-fire-extinguisher',
					href: '/applied-controls'
				},
			]
		},
		{
			name: 'governance',
			items: [
				{
					name: 'assetInventory',
					fa_icon: 'fa-solid fa-gem',
					href: '/assets',
				},
				{
					name: 'policiesAndProcedures',
					fa_icon: 'fa-solid fa-user',
					href: '/policies',
					permissions: ['view_appliedcontrol']
				},
				{
					name: 'trainingAndEduction',
					fa_icon: 'fa-solid fa-graduation-cap',
					href: '/policies',
				},
				{
					name: 'changeManagement',
					fa_icon: 'fa-solid fa-wrench',
					href: '/policies',
				},
				{
					name: 'incidentManagement',
					fa_icon: 'fa-solid fa-medkit',
					href: '/policies',
				},
				{
					name: 'configurationManagement',
					fa_icon: 'fa-solid fa-tasks',
					href: '/policies',
				},
				{
					name: 'patchManagement',
					fa_icon: 'fa-solid fa-sitemap',
					href: '/policies',
				},
				{
					name: 'thirdPartyAuditReports',
					fa_icon: 'fa-solid fa-table',
					href: '/policies',
				},
				{
					name: 'reports',
					fa_icon: 'fa-solid fa-book',
					href: '/policies',
				},
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
				},
				{
					name: 'riskRegister',
					fa_icon: 'fa-solid fa-book',
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
					name: 'complianceAuditReports',
					fa_icon: 'fa-solid fa-book',
					href: '/compliance-assessments' // update path
				},
			]
		},
		{
			name: 'organization',
			items: [
				{
					name: 'domains',
					fa_icon: 'fa-solid fa-diagram-project',
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
			name: 'config',
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
