<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import { getOptions } from '$lib/utils/crud';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import { BASE_API_URL } from '$lib/utils/constants';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};

	export let updated_fields: Set<string> = new Set();

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
	options={getOptions({
		objects: model.foreignKeys['risk_assessment'],
		label: 'str',
		extra_fields: [['project', 'str']]
	})}
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
	options={getOptions({
		objects: model.foreignKeys['threats'],
		extra_fields: [['folder', 'str']],
		label: 'auto'
	})}
	field="threats"
	cacheLock={cacheLocks['threats']}
	bind:cachedValue={formDataCache['threats']}
	label={m.threats()}
/>
