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
		[key: string]: any;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		updated_fields = new Set(),
		object,
		...rest
	}: Props = $props();

	let isParentLocked = $derived(object?.risk_assessment?.is_locked || false);

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

	const scopeFolder = $derived(rest?.scopeFolder || { id: '' });
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
	onChange={async (e) => {
		if (e) {
			await fetchDefaultRefId(e);
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
	optionsDetailedUrlParameters={[
		scopeFolder?.id ? ['scope_folder_id', scopeFolder.id] : ['', undefined]
	]}
	optionsInfoFields={{
		fields: [
			{
				field: 'type'
			}
		],
		classes: 'text-blue-500'
	}}
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
	optionsDetailedUrlParameters={[
		scopeFolder?.id ? ['scope_folder_id', scopeFolder.id] : ['', undefined]
	]}
	optionsLabelField="auto"
	field="threats"
	cacheLock={cacheLocks['threats']}
	bind:cachedValue={formDataCache['threats']}
	label={m.threats()}
/>
