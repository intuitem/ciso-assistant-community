<script lang="ts">
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context?: string;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = 'create'
	}: Props = $props();

	const isBuiltin = $derived(object?.origin === 'builtin');

	onMount(async () => {
		if (!model.selectOptions) {
			const [statusOpts, typeOpts] = await Promise.all([
				fetch('/document-templates/status').then((r) => r.json()),
				fetch('/document-templates/document_type').then((r) => r.json())
			]);
			model.selectOptions = {
				status: statusOpts,
				document_type: typeOpts
			};
		}
	});
</script>

{#if isBuiltin}
	<div class="card p-3 preset-tonal-warning text-sm">
		<i class="fa-solid fa-lock mr-2"></i>{m.builtinTemplateLockedHelp()}
	</div>
{/if}

<TextField
	{form}
	field="name"
	label={m.name()}
	disabled={isBuiltin}
	cacheLock={cacheLocks['name']}
	bind:cachedValue={formDataCache['name']}
/>

<TextArea
	{form}
	field="description"
	label={m.description()}
	disabled={isBuiltin}
	cacheLock={cacheLocks['description']}
	bind:cachedValue={formDataCache['description']}
/>

<Select
	{form}
	options={model.selectOptions?.document_type}
	field="document_type"
	label={m.documentType()}
	disabled={isBuiltin}
	disableDoubleDash={true}
	cacheLock={cacheLocks['document_type']}
	bind:cachedValue={formDataCache['document_type']}
/>

<Select
	{form}
	options={model.selectOptions?.status}
	field="status"
	label={m.status()}
	disableDoubleDash={true}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>

<FolderTreeSelect
	{form}
	field="folder"
	disabled={isBuiltin}
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>

<TextField
	{form}
	field="locale"
	label={m.locale()}
	disabled={isBuiltin}
	cacheLock={cacheLocks['locale']}
	bind:cachedValue={formDataCache['locale']}
/>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	disabled={isBuiltin}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

<TextArea
	{form}
	field="content"
	label={m.content()}
	rows={20}
	disabled={isBuiltin}
	cacheLock={cacheLocks['content']}
	bind:cachedValue={formDataCache['content']}
/>
