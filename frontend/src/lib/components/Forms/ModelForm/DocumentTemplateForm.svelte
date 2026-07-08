<script lang="ts">
	import Select from '../Select.svelte';
	import TextField from '../TextField.svelte';
	import MarkdownField from '../MarkdownField.svelte';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	import { DOCUMENT_TYPES } from '$lib/utils/documentTypes';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = ''
	}: Props = $props();

	const documentTypeOptions = DOCUMENT_TYPES.map((t) => ({
		label: t.label(),
		value: t.key
	}));
	const localeOptions = Object.keys(LOCALE_MAP).map((code) => ({
		label: code.toUpperCase(),
		value: code
	}));
</script>

<Select
	{form}
	options={documentTypeOptions}
	field="document_type"
	label={m.documentType()}
	cacheLock={cacheLocks['document_type']}
	bind:cachedValue={formDataCache['document_type']}
/>
<Select
	{form}
	options={localeOptions}
	field="locale"
	label={m.language()}
	cacheLock={cacheLocks['locale']}
	bind:cachedValue={formDataCache['locale']}
/>
<TextField
	{form}
	field="provider"
	label={m.provider()}
	cacheLock={cacheLocks['provider']}
	bind:cachedValue={formDataCache['provider']}
/>
<!-- Content is authored on the edit view, not in the cramped create modal. -->
{#if object?.id}
	<MarkdownField
		{form}
		field="content"
		label={m.content()}
		cacheLock={cacheLocks['content']}
		bind:cachedValue={formDataCache['content']}
	/>
{/if}
