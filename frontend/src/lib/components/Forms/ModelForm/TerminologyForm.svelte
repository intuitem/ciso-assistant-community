<script lang="ts">
	import Checkbox from '../Checkbox.svelte';
	import Select from '../Select.svelte';
	import TextField from '../TextField.svelte';
	import MarkdownField from '../MarkdownField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

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
<Checkbox {form} field="is_visible" label={m.isVisible()} helpText={m.isVisibleHelpText()} />
