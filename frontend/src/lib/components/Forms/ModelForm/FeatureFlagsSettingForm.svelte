<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	import BackgroundCheckbox from '$lib/components/Forms/BackgroundCheckbox.svelte';

	interface Props {
		form: SuperValidated<any>;
	}

	let { form }: Props = $props();

	const featureFlagGroups = [
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
				}
			]
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
					label: m.followUp(),
					description: m.findingsAssessmentsDescription()
				},
				{
					field: 'metrology',
					label: m.metrology(),
					description: m.metrologyDescription()
				}
			]
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
					field: 'validation_flows',
					label: m.validationFlows(),
					description: m.validationFlowsDescription()
				}
			]
		},
		{
			category: m.complianceRiskManagement(),
			description: m.complianceRiskManagementDescription(),
			fields: [
				{
					field: 'compliance',
					label: m.compliance(),
					description: m.complianceAssessmentsDescription()
				},
				{
					field: 'privacy',
					label: m.privacy(),
					description: m.privacyDescription()
				},
				{
					field: 'risk_acceptances',
					label: m.riskAcceptances(),
					description: m.riskAcceptancesDescription()
				},
				{
					field: 'exceptions',
					label: m.securityExceptions(),
					description: m.securityExceptionsDescription()
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
					field: 'scoring_assistant',
					label: m.scoringAssistant(),
					description: m.scoringAssistantDescription()
				},
				{
					field: 'bia',
					label: m.businessImpactAnalysis(),
					description: m.businessImpactAnalysisDescription()
				}
			]
		},
		{
			category: m.extra(),
			description: m.extraDescription(),
			fields: [
				{
					field: 'terminologies',
					label: m.terminologies(),
					description: m.riskOriginHelpText()
				},
				{
					field: 'outgoing_webhooks',
					label: m.webhooks(),
					description: m.webhooksDescription()
				},
				{
					field: 'experimental',
					label: m.experimental(),
					description: m.experimentalFeatures()
				}
			]
		}
	];
</script>

<div class="space-y-6">
	{#each featureFlagGroups as group}
		<div class="bg-white shadow-sm rounded-xl p-6 border border-gray-200">
			<div class="mb-4">
				<h2 class="text-xl font-bold text-gray-800">{group.category}</h2>
				<p class="text-sm text-gray-500 mt-1">{group.description}</p>
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
				{#each group.fields as { field, label, description }}
					<BackgroundCheckbox {form} {field} {label} helpText={description} />
				{/each}
			</div>
		</div>
	{/each}
</div>
