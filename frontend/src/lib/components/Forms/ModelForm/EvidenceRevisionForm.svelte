<script lang="ts">
	import HiddenInput from '../HiddenInput.svelte';
	import FileInput from '../FileInput.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import NumberField from '../NumberField.svelte';

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

	function getFilename(path) {
		if (!path) return '';

		try {
			// If it's a URL with query parameters
			const withoutQuery = path.split('?')[0];
			// Get the last part after the final slash (if any)
			return decodeURIComponent(withoutQuery.split('/').pop());
		} catch (e) {
			return path; // Fallback to original string if anything fails
		}
	}
</script>

<HiddenInput {form} field="evidence" />
<HiddenInput {form} field="folder" />

{#if context === 'edit'}
	<NumberField
		{form}
		field="version"
		label={m.version()}
		cacheLock={cacheLocks['version']}
		bind:cachedValue={formDataCache['version']}
	/>
{/if}
<FileInput
	{form}
	allowPaste={true}
	helpText={object.attachment
		? `${m.attachmentWarningText()}: ${getFilename(object.attachment)}`
		: m.attachmentHelpText()}
	field="attachment"
	label={m.attachment()}
	allowedExtensions={'*'}
/>
<!-- {#if !(initialData.applied_controls || initialData.requirement_assessments || initialData.evidence)}
	<AutocompleteSelect
		{form}
		optionsEndpoint="folders?content_type=DO&content_type=GL"
		field="folder"
		pathField="path"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.domain()}
		hidden={initialData.applied_controls ||
			initialData.requirement_assessments ||
			initialData.folder}
	/>
{:else}
	<HiddenInput {form} field="folder" />
{/if} -->
<TextField
	{form}
	field="link"
	label={m.link()}
	helpText={m.linkHelpText()}
	cacheLock={cacheLocks['link']}
	bind:cachedValue={formDataCache['link']}
/>
<TextArea
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
