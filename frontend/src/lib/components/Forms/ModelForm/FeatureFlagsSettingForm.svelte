<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';

	interface Props {
		form: SuperValidated<any>;
	}

	let { form }: Props = $props();

	// Config for feature flags
	const featureFlagFields = [
		{ field: 'xrays', label: m.xRays() },
		{ field: 'incidents', label: m.incidents() },
		{ field: 'tasks', label: m.tasks() },
		{ field: 'risk_acceptances', label: m.riskAcceptances() },
		{ field: 'exceptions', label: m.securityExceptions() },
		{ field: 'follow_up', label: m.followUp() },
		{ field: 'ebiosrm', label: m.ebiosRM() },
		{ field: 'scoring_assistant', label: m.scoringAssistant() },
		{ field: 'vulnerabilities', label: m.vulnerabilities() },
		{ field: 'compliance', label: m.compliance() },
		{ field: 'tprm', label: m.thirdParty() },
		{ field: 'privacy', label: m.privacy() },
		{ field: 'experimental', label: m.experimental() },
		{ field: 'inherent_risk', label: m.inherentRisk() },
		{ field: 'organisation_objectives', label: m.organisationObjectives() },
		{ field: 'organisation_issues', label: m.organisationIssues() },
		{ field: 'quantitative_risk_studies', label: m.quantitativeRiskStudies() },
		{ field: 'terminologies', label: m.terminologies() },
		{ field: 'bia', label: m.businessImpactAnalysis() },
		{ field: 'project_management', label: m.projectManagement() }
	];
</script>

<div
	class="mx-auto grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 gap-y-2 gap-x-4"
>
	{#each featureFlagFields as { field, label }}
		<div class="ml-auto">
			<Checkbox {form} {field} {label} />
		</div>
	{/each}
</div>
