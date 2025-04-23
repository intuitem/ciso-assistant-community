<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	import { ffNav } from '$lib/components/SideBar/ffNav';
	export let data: any = {};

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
		{ field: 'experimental', label: m.experimental() }
	];
</script>

{#each featureFlagFields as { field, label }}
	<Checkbox {form} {field} {label} />
{/each}
