<script lang="ts">
	import HiddenInput from '../HiddenInput.svelte';
	import FileInput from '../FileInput.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: any = {};
</script>

{#if model.urlModel === 'evidences'}
	<HiddenInput {form} field="applied_controls" />
	<HiddenInput {form} field="requirement_assessments" />
	<FileInput
		{form}
		allowPaste={true}
		helpText={object.attachment
			? `${m.attachmentWarningText()}: ${object.attachment}`
			: m.attachmentHelpText()}
		field="attachment"
		label={m.attachment()}
	/>
	{#if !(initialData.applied_controls || initialData.requirement_assessments)}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hidden={initialData.applied_controls || initialData.requirement_assessments}
		/>
	{:else}
		<HiddenInput {form} field="folder" />
	{/if}
	<TextField
		{form}
		field="link"
		label={m.link()}
		helpText={m.linkHelpText()}
		cacheLock={cacheLocks['link']}
		bind:cachedValue={formDataCache['link']}
	/>
{/if}
