<script lang="ts">
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
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

<FolderTreeSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>

<TextField
	{form}
	field="code"
	cacheLock={cacheLocks['code']}
	bind:cachedValue={formDataCache['code']}
	label={m.code()}
	helpText={m.responsibilityRoleCodeHelpText()}
/>

<TextField
	{form}
	field="name"
	cacheLock={cacheLocks['name']}
	bind:cachedValue={formDataCache['name']}
	label={m.name()}
/>

<TextArea
	{form}
	field="description"
	label={m.description()}
	cacheLock={cacheLocks['description']}
	bind:cachedValue={formDataCache['description']}
/>

<Select
	{form}
	field="taxonomy"
	cacheLock={cacheLocks['taxonomy']}
	bind:cachedValue={formDataCache['taxonomy']}
	options={[
		{ value: 'raci', label: 'RACI' },
		{ value: 'rasci', label: 'RASCI' },
		{ value: 'rapid', label: 'RAPID' },
		{ value: 'custom', label: m.custom() }
	]}
	label={m.taxonomy()}
/>

<TextField
	{form}
	field="color"
	cacheLock={cacheLocks['color']}
	bind:cachedValue={formDataCache['color']}
	label={m.color()}
	helpText={m.responsibilityRoleColorHelpText()}
/>

<TextField
	type="number"
	{form}
	field="order"
	cacheLock={cacheLocks['order']}
	bind:cachedValue={formDataCache['order']}
	label={m.order()}
/>

<Checkbox {form} field="is_visible" label={m.isVisible()} />
