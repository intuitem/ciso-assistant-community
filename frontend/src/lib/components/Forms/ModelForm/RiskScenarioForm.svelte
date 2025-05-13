<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';


	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		updated_fields?: Set<string>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		updated_fields = new Set()
	}: Props = $props();

	async function fetchDefaultRefId(riskAssessmentId: string) {
		try {
			const response = await fetch(
				`/risk-scenarios/default-ref-id/?risk_assessment=${riskAssessmentId}`
			);
			const result = await response.json();
			if (response.ok && result.results) {
				form.form.update((currentData) => {
					updated_fields.add('ref_id');
					return { ...currentData, ref_id: result.results };
				});
			} else {
				console.error(result.error || 'Failed to fetch default ref_id');
			}
		} catch (error) {
			console.error('Error fetching default ref_id:', error);
		}
	}
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="risk-assessments"
	optionsExtraFields={[['perimeter', 'str']]}
	optionsLabelField="str"
	field="risk_assessment"
	cacheLock={cacheLocks['risk_assessment']}
	bind:cachedValue={formDataCache['risk_assessment']}
	label={m.riskAssessment()}
	hidden={initialData.risk_assessment}
	on:change={async (e) => {
		if (e.detail) {
			await fetchDefaultRefId(e.detail);
		}
	}}
/>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="assets"
	cacheLock={cacheLocks['assets']}
	bind:cachedValue={formDataCache['assets']}
	label={m.assets()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="threats"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="threats"
	cacheLock={cacheLocks['threats']}
	bind:cachedValue={formDataCache['threats']}
	label={m.threats()}
/>
