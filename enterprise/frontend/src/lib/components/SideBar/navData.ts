export const navData = {
	items: [
		{
			name: 'overview',
			items: [
				{
					name: 'analytics',
					fa_icon: 'fa-solid fa-gauge',
					href: '/analytics',
					permissions: [
						'view_perimeter',
						'view_riskscenario',
						'view_referencecontrol',
						'view_assessment',
						'view_riskassessment'
					]
				},
				{
					name: 'domainAnalytics',
					fa_icon: 'fa-solid fa-folder-tree',
					href: '/domain-analytics',
					permissions: [
						'view_perimeter',
						'view_riskscenario',
						'view_referencecontrol',
						'view_assessment',
						'view_riskassessment'
					]
				},
				{
					name: 'myAssignments',
					fa_icon: 'fa-solid fa-list-check',
					href: '/my-assignments',
					permissions: [
						'view_perimeter',
						'view_riskscenario',
						'view_referencecontrol',
						'view_assessment',
						'view_riskassessment'
					]
				}
			]
		},
		{
			name: 'insights',
			items: [
				{
					name: 'impactAnalysis',
					fa_icon: 'fa-solid fa-hexagon-nodes',
					href: '/insights/impact-analysis',
					permissions: [
						'view_perimeter',
						'view_riskscenario',
						'view_referencecontrol',
						'view_assessment',
						'view_riskassessment'
					]
				},
				{
					name: 'priorityReview',
					fa_icon: 'fa-solid fa-ranking-star',
					href: '/insights/priority-review',
					permissions: [
						'view_perimeter',
						'view_riskscenario',
						'view_referencecontrol',
						'view_assessment',
						'view_riskassessment'
					]
				},
				{
					name: 'timelineView',
					fa_icon: 'fa-solid fa-table-columns',
					href: '/insights/timeline-view',
					permissions: [
						'view_perimeter',
						'view_riskscenario',
						'view_referencecontrol',
						'view_assessment',
						'view_riskassessment'
					]
				}
			]
		},
		{
			name: 'organization',
			items: [
				{
					name: 'domains',
					fa_icon: 'fa-solid fa-sitemap',
					href: '/folders',
					exclude: ['BI-RL-TPR']
				},
				{
					name: 'perimeters',
					fa_icon: 'fa-solid fa-cubes',
					href: '/perimeters'
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
				},
				{
					name: 'assets',
					fa_icon: 'fa-solid fa-gem',
					href: '/assets'
				}
			]
		},
		{
			name: 'catalog',
			items: [
				{
					name: 'frameworks',
					fa_icon: 'fa-solid fa-book',
					href: '/frameworks'
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
					name: 'requirementMappingSets',
					fa_icon: 'fa-solid fa-diagram-project',
					href: '/requirement-mapping-sets'
				},
				{
					name: 'riskMatrices',
					fa_icon: 'fa-solid fa-table-cells-large',
					href: '/risk-matrices'
				}
			]
		},
		{
			name: 'operations',
			items: [
				{
					name: 'appliedControls',
					fa_icon: 'fa-solid fa-fire-extinguisher',
					href: '/applied-controls'
				},
				{
					name: 'calendar',
					fa_icon: 'fa-solid fa-calendar-days',
					href: '/calendar',
					permissions: ['view_appliedcontrol', 'view_riskacceptance', 'view_riskassessment']
				},
				{
					name: 'xRays',
					fa_icon: 'fa-solid fa-bolt',
					href: '/x-rays',
					permissions: ['view_riskassessment', 'view_assessment']
				},
				{
					name: 'incidents',
					fa_icon: 'fa-solid fa-bug',
					href: '/incidents'
				},
				{
					name: 'tasks',
					fa_icon: 'fa-solid fa-note-sticky',
					href: '/task-templates'
				}
			]
		},
		{
			name: 'governance',
			items: [
				{
					name: 'libraries',
					fa_icon: 'fa-solid fa-folder-plus',
					href: '/libraries',
					permissions: ['add_threat', 'add_riskmatrix', 'add_referencecontrol', 'add_framework']
				},
				{
					name: 'policies',
					fa_icon: 'fa-solid fa-book',
					href: '/policies',
					permissions: ['view_appliedcontrol']
				},
				{
					name: 'riskAcceptances',
					fa_icon: 'fa-solid fa-signature',
					href: '/risk-acceptances'
				},
				{
					name: 'securityExceptions',
					fa_icon: 'fa-solid fa-circle-exclamation',
					href: '/security-exceptions'
				},
				{
					name: 'followUp',
					fa_icon: 'fa-solid fa-clipboard-list',
					href: '/findings-assessments'
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
					name: 'ebiosRM',
					fa_icon: 'fa-solid fa-gopuram',
					href: '/ebios-rm'
				},
				{
					name: 'riskScenarios',
					fa_icon: 'fa-solid fa-clone',
					href: '/risk-scenarios'
				},
				{
					name: 'scoringAssistant',
					fa_icon: 'fa-solid fa-star-half-stroke',
					href: '/scoring-assistant',
					permissions: ['view_riskmatrix']
				},
				{
					name: 'vulnerabilities',
					// What is the best icon between "fa-triangle-exclamation" and "fa-skull-crossbones" for a vulnerability ?
					fa_icon: 'fa-solid fa-triangle-exclamation',
					href: '/vulnerabilities'
				}
			]
		},

		{
			name: 'compliance',
			items: [
				{
					name: 'complianceAssessments',
					fa_icon: 'fa-solid fa-certificate',
					href: '/compliance-assessments'
				},
				{
					name: 'evidences',
					fa_icon: 'fa-solid fa-receipt',
					href: '/evidences'
				},
				{
					name: 'recap',
					fa_icon: 'fa-solid fa-clipboard-list',
					href: '/recap',
					permissions: ['view_complianceassessment']
				}
			]
		},

		{
			name: 'thirdPartyCategory',
			items: [
				{
					name: 'tprmOverview',
					fa_icon: 'fa-solid fa-gauge',
					href: '/analytics/tprm',
					permissions: [
						'view_complianceassessment',
						'view_entity',
						'view_solution',
						'view_entityassessment'
					]
				},
				{
					name: 'entities',
					fa_icon: 'fa-solid fa-building',
					href: '/entities'
				},
				{
					name: 'entityAssessments',
					fa_icon: 'fa-solid fa-clipboard-list',
					href: '/entity-assessments'
				},
				{
					name: 'representatives',
					fa_icon: 'fa-solid fa-user-tie',
					href: '/representatives'
				},
				{
					name: 'solutions',
					fa_icon: 'fa-solid fa-box',
					href: '/solutions'
				}
			]
		},
		{
			name: 'privacy',
			items: [
				{
					name: 'overview',
					fa_icon: 'fa-solid fa-gauge',
					href: '/analytics/gdpr',
					permissions: ['view_processing', 'view_purpose']
				},
				{
					name: 'processingsRegister',
					fa_icon: 'fa-solid fa-clipboard-list',
					href: '/processings',
					permissions: ['view_processing']
				},
				{
					name: 'personalData',
					fa_icon: 'fa-solid fa-users-viewfinder',
					href: '/personal-data',
					permissions: ['view_personaldata']
				},
				{
					name: 'purposes',
					fa_icon: 'fa-solid fa-diamond',
					href: '/purposes',
					permissions: ['view_purpose']
				}
			]
		},
		{
			name: 'extra',
			items: [
				{
					name: 'labels',
					fa_icon: 'fa-solid fa-tag',
					href: '/filtering-labels',
					permissions: ['view_filteringlabel']
				},
				{
					name: 'settings',
					fa_icon: 'fa-solid fa-cog',
					href: '/settings',
					permissions: ['change_globalsettings']
				},
				{
					name: 'backupRestore',
					fa_icon: 'fa-solid fa-floppy-disk',
					href: '/backup-restore',
					permissions: ['backup']
				},
				{
					name: 'Experimental',
					fa_icon: 'fa-solid fa-flask',
					href: '/experimental',
					permissions: ['change_globalsettings']
				}
			]
		}
	]
};
