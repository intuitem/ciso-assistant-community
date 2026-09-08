<script lang="ts">
	import HiddenInput from '../HiddenInput.svelte';
	import EvidenceFilesInput from '../EvidenceFilesInput.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		context: string;
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
		object = {},
		context
	}: Props = $props();
</script>

<HiddenInput {form} field="evidence" />
<HiddenInput {form} field="task_node" />

{#if context === 'edit'}
	<div>
		<span class="text-sm font-semibold">{m.version()}</span>
		<p class="text-sm text-surface-600-400">{object.version}</p>
	</div>
{/if}

<EvidenceFilesInput
	{form}
	existing={context === 'edit' ? (object.attachments?.length ?? (object.attachment ? 1 : 0)) : 0}
/>
<TextField
	{form}
	field="link"
	label={m.link()}
	helpText={m.linkHelpText()}
	cacheLock={cacheLocks['link']}
	bind:cachedValue={formDataCache['link']}
/>
<MarkdownField
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
