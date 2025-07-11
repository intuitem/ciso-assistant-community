<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context?: {
			selectElementaryActions?: boolean;
		};
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context = {},
		updated_fields = new Set()
	}: Props = $props();

	async function fetchDefaultRefId(operationalScenarioId: string) {
		try {
			const response = await fetch(
				`/operating-modes/default-ref-id/?operational_scenario=${operationalScenarioId}`
			);
			console.log(response);
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

{#if context !== 'selectElementaryActions'}
	<AutocompleteSelect
		{form}
		optionsEndpoint="operational-scenarios"
		field="operational_scenario"
		cacheLock={cacheLocks['operational_scenario']}
		bind:cachedValue={formDataCache['operational_scenario']}
		label={m.operationalScenario()}
		hidden
		onChange={async (e) => fetchDefaultRefId(e)}
		mount={async (e) => fetchDefaultRefId(e)}
	/>
	<TextField
		{form}
		field="ref_id"
		label={m.refId()}
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
	/>
	<Select
		{form}
		options={model.selectOptions['likelihood']}
		field="likelihood"
		label={m.likelihood()}
		cacheLock={cacheLocks['likelihood']}
		bind:cachedValue={formDataCache['likelihood']}
		helpText={m.likelihoodHelpText()}
	/>
{:else}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="elementary-actions"
		optionsInfoFields={{
			fields: [
				{
					field: 'attack_stage',
					translate: true
				}
			],
			classes: 'text-yellow-700'
		}}
		field="elementary_actions"
		cacheLock={cacheLocks['elementary_actions']}
		bind:cachedValue={formDataCache['elementary_actions']}
		label={m.elementaryActions()}
	/>
{/if}
