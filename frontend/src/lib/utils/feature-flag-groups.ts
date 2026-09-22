import { m } from '$paraglide/messages';

export interface FeatureFlagField {
	field: string;
	label: string;
	description: string;
}

export interface FeatureFlagGroup {
	category: string;
	description: string;
	fields: FeatureFlagField[];
}

/**
 * The flag taxonomy, shared by the instance settings form and the per-user module
 * preferences so labels and grouping cannot drift.
 *
 * `availableKeys` narrows it to what the caller may show — every exposed flag for
 * the admin form, only the hideable ones for the profile page. Empty groups drop.
 */
export function getFeatureFlagGroups(availableKeys: string[]): FeatureFlagGroup[] {
	return [
		{
			category: m.organization(),
			description: m.organisationDescription(),
			fields: [
				{
					field: 'organisation_objectives',
					label: m.organisationObjectives(),
					description: m.organisationObjectivesDescription()
				},
				{
					field: 'organisation_issues',
					label: m.organisationIssues(),
					description: m.organisationIssuesDescription()
				},
				{
					field: 'journeys',
					label: m.journeys(),
					description: m.journeysDescription()
				},
				{
					field: 'custom_portals',
					label: m.customPortals(),
					description: m.customPortalsDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.catalog(),
			description: m.CatalogDescription(),
			fields: [
				{
					field: 'security_advisories',
					label: m.securityAdvisories(),
					description: m.securityAdvisoriesDescription()
				},
				{
					field: 'cwes',
					label: m.cwe(),
					description: m.cweDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.operations(),
			description: m.operationsDescription(),
			fields: [
				{
					field: 'tasks',
					label: m.tasks(),
					description: m.taskTemplatesDescription()
				},
				{
					field: 'control_plan',
					label: m.tasksReview(),
					description: m.controlPlanDescription()
				},
				{
					field: 'xrays',
					label: m.xRays(),
					description: m.xRaysDescription()
				},
				{
					field: 'incidents',
					label: m.incidents(),
					description: m.incidentsDescription()
				},
				{
					field: 'follow_up',
					label: m.findingsManagement(),
					description: m.findingsAssessmentsDescription()
				},
				{
					field: 'metrology',
					label: m.metrology(),
					description: m.metrologyDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.assetClassManagementAndGovernance(),
			description: m.assetClassManagementAndGovernanceDescription(),
			fields: [
				{
					field: 'project_management',
					label: m.projectManagement(),
					description: m.projectManagementDescription()
				},
				{
					field: 'reports',
					label: m.reports(),
					description: m.reportsDescription()
				},
				{
					field: 'tprm',
					label: m.thirdParty(),
					description: m.thirdPartyDescription()
				},
				{
					field: 'contracts',
					label: m.contracts(),
					description: m.contractsDescription()
				},
				{
					field: 'external_ratings',
					label: m.externalRatings(),
					description: m.externalRatingsDescription()
				},
				{
					field: 'validation_flows',
					label: m.validationFlows(),
					description: m.validationFlowsDescription()
				},
				{
					field: 'workflows',
					label: m.workflows(),
					description: m.workflowsFlagDescription()
				},
				{
					field: 'policy_documents',
					label: m.policyDocumentsFlag(),
					description: m.policyDocumentsFlagDescription()
				},
				{
					field: 'document_management',
					label: m.documentManagementFlag(),
					description: m.documentManagementFlagDescription()
				},
				{
					field: 'exceptions',
					label: m.securityExceptions(),
					description: m.securityExceptionsDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.compliance(),
			description: m.complianceDescription(),
			fields: [
				{
					field: 'compliance',
					label: m.compliance(),
					description: m.complianceAssessmentsDescription()
				},
				{
					field: 'campaigns',
					label: m.campaigns(),
					description: m.campaignsDescription()
				},
				{
					field: 'findings_from_requirements',
					label: m.findingsFromRequirements(),
					description: m.findingsFromRequirementsDescription()
				},
				{
					field: 'auditee_mode',
					label: m.auditeeMode(),
					description: m.auditeeModeDescription()
				},
				{
					field: 'quick_forms',
					label: m.formsAndRequests(),
					description: m.formsAndRequestsDescription()
				},
				{
					field: 'advanced_analytics',
					label: m.advancedAnalytics(),
					description: m.advancedAnalyticsDescription()
				},
				{
					field: 'audit_tree_inheritance',
					label: m.auditTreeInheritance(),
					description: m.auditTreeInheritanceDescription()
				},
				{
					field: 'posture_assessments',
					label: m.postureAssessments(),
					description: m.postureAssessmentsDescription()
				},
				{
					field: 'commitment_management',
					label: m.commitmentManagement(),
					description: m.commitmentManagementDescription()
				},
				{
					field: 'dora',
					label: m.dora(),
					description: m.doraFlagDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.riskManagement(),
			description: m.riskManagementDescription(),
			fields: [
				{
					field: 'risk_acceptances',
					label: m.riskAcceptances(),
					description: m.riskAcceptancesDescription()
				},
				{
					field: 'inherent_risk',
					label: m.inherentRisk(),
					description: m.inherentRiskLevelHelpText()
				},
				{
					field: 'vulnerabilities',
					label: m.vulnerabilities(),
					description: m.vulnerabilitiesDescription()
				},
				{
					field: 'ebiosrm',
					label: m.ebiosRM(),
					description: m.ebiosRmDescription()
				},
				{
					field: 'quantitative_risk_studies',
					label: m.quantitativeRiskStudies(),
					description: m.quantitativeRiskStudiesDescription()
				},
				{
					field: 'threat_modeling',
					label: m.threatModeling(),
					description: m.threatModelingDescription()
				},
				{
					field: 'ttps',
					label: m.ttpCatalogs(),
					description: m.ttpsDescription()
				},
				{
					field: 'scoring_assistant',
					label: m.scoringAssistant(),
					description: m.scoringAssistantDescription()
				},
				{
					field: 'bia',
					label: m.businessImpactAnalysis(),
					description: m.businessImpactAnalysisDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.gdpr(),
			description: m.gdprDescription(),
			fields: [
				{
					field: 'privacy',
					label: m.privacy(),
					description: m.privacyDescription()
				},
				{
					field: 'personal_data',
					label: m.personalData(),
					description: m.personalDataDescription()
				},
				{
					field: 'purposes',
					label: m.purposes(),
					description: m.purposesDescription()
				},
				{
					field: 'right_requests',
					label: m.rightRequests(),
					description: m.rightRequestsDescription()
				},
				{
					field: 'data_breaches',
					label: m.dataBreaches(),
					description: m.dataBreachesDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		},
		{
			category: m.extra(),
			description: m.extraDescription(),
			fields: [
				{
					field: 'focus_mode',
					label: m.focusMode(),
					description: m.focusModeTooltip()
				},
				{
					field: 'idp_groups',
					label: m.idpGroups(),
					description: m.idpGroupsDescription()
				},
				{
					field: 'jit_provisioning',
					label: m.jitProvisioning(),
					description: m.jitProvisioningDescription()
				},
				{
					field: 'service_accounts',
					label: m.serviceAccounts(),
					description: m.serviceAccountsDescription()
				},
				{
					field: 'terminologies',
					label: m.terminologies(),
					description: m.riskOriginHelpText()
				},
				{
					field: 'custom_fields',
					label: m.customFields(),
					description: m.customFieldsDescription()
				},
				{
					field: 'outgoing_webhooks',
					label: m.webhooks(),
					description: m.webhooksDescription()
				},
				{
					field: 'audit_log_forwarding',
					label: m.auditLogForwarding(),
					description: m.auditLogForwardingDescription()
				},
				{
					field: 'comments',
					label: m.comments(),
					description: m.commentsDescription()
				},
				{
					field: 'relations_graph',
					label: m.relationsGraph(),
					description: m.relationsGraphDescription()
				},
				{
					field: 'experimental',
					label: m.experimental(),
					description: m.experimentalFeatures()
				},
				{
					field: 'chat_mode',
					label: m.chatMode(),
					description: m.chatModeDescription()
				},
				{
					field: 'object_audit_trail',
					label: m.objectAuditTrail(),
					description: m.objectAuditTrailDescription()
				}
			].filter(({ field }) => availableKeys.includes(field))
		}
	].filter((group) => group.fields.length > 0);
}
