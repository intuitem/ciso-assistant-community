<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {}
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	field="legal_basis"
	options={model.selectOptions['legal_basis']}
	cacheLock={cacheLocks['legal_basis']}
	bind:cachedValue={formDataCache['legal_basis']}
	label={m.legalBasis()}
/>
<AutocompleteSelect
	{form}
	field="article_9_condition"
	options={model.selectOptions['article_9_condition']}
	cacheLock={cacheLocks['article_9_condition']}
	bind:cachedValue={formDataCache['article_9_condition']}
	label={m.article9Condition()}
/>
<AutocompleteSelect
	{form}
	field="processing"
	optionsEndpoint="processings"
	cacheLock={cacheLocks['processing']}
	bind:cachedValue={formDataCache['processing']}
	label={m.processing()}
	hidden={initialData.processing}
/>

<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<TextField
		{form}
		field="ref_id"
		label={m.refId()}
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
	/>
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
	/>
	<MarkdownField
		{form}
		field="description"
		label={m.description()}
		cacheLock={cacheLocks['description']}
		bind:cachedValue={formDataCache['description']}
	/>
</Dropdown>
