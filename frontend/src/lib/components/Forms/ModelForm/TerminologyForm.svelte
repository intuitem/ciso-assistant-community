<script lang="ts">
	import Checkbox from '../Checkbox.svelte';
	import Select from '../Select.svelte';
	import TextField from '../TextField.svelte';
	import MarkdownField from '../MarkdownField.svelte';
	import TranslationField from '../TranslationField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();
</script>

{#if !object.builtin}
	<Select
		{form}
		options={model.selectOptions['field_path']}
		field="field_path"
		label={m.fieldPath()}
		cacheLock={cacheLocks['field_path']}
		bind:cachedValue={formDataCache['field_path']}
	/>
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
		data-focusindex="0"
	/>
	<MarkdownField
		{form}
		field="description"
		label={m.description()}
		cacheLock={cacheLocks['description']}
		bind:cachedValue={formDataCache['description']}
		data-focusindex="1"
	/>
	<TranslationField
		{form}
		field="translations"
		cacheLock={cacheLocks['translations']}
		bind:cachedValue={formDataCache['translations']}
	/>
{/if}
<Checkbox {form} field="is_visible" label={m.isVisible()} helpText={m.isVisibleHelpText()} />
