<script lang="ts">
	import Select from '../Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import HiddenInput from '$lib/components/Forms/HiddenInput.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		context: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		context
	}: Props = $props();
</script>

{#if context === 'selectEvidences'}
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="evidences"
		optionsExtraFields={[['folder', 'str']]}
		field="evidences"
		label={m.evidences()}
	/>
{:else}
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<Select
		{form}
		options={model.selectOptions['result']}
		field="result"
		label={m.result()}
		cacheLock={cacheLocks['result']}
		bind:cachedValue={formDataCache['result']}
	/>
	<TextArea
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	<HiddenInput {form} field="folder" />
	<HiddenInput {form} field="requirement" />
	<HiddenInput {form} field="compliance_assessment" />
{/if}
