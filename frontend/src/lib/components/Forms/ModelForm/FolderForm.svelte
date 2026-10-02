<script lang="ts">
	import * as m from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import FileInput from '../FileInput.svelte';
	import Checkbox from '../Checkbox.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderIAMGroupsSelect from '../FolderIAMGroupsSelect.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';

	interface Props {
		form: SuperValidated<any>;
		importFolder?: boolean;
		// and there is only one ModelForm.
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		model: ModelInfo;
	}

	// Props unused but referenced to avoid browser warnings because they're needed for enterprise Folderform
	let {
		form,
		importFolder = false,
		cacheLocks = {},
		formDataCache = {},
		initialData = {},
		object = {},
		model
	}: Props = $props();

	// IAM groups only work for normal folders (not for enclave/root folders).
	let displayIAMGroups = $derived(object.content_type === 'DO');
</script>

{#if importFolder}
	<FileInput
		{form}
		allowPaste={true}
		field="file"
		label={m.file()}
		allowedExtensions={['bak', 'zip']}
		helpText={m.importFolderHelpText()}
	/>
	<Checkbox
		{form}
		field="load_missing_libraries"
		label={m.loadMissingLibraries()}
		helpText={m.loadMissingLibrariesHelpText()}
	/>
	<Checkbox
		{form}
		field="create_missing_asset_classes"
		label={m.createMissingAssetClasses()}
		helpText={m.createMissingAssetClassesHelpText()}
	/>
{:else}
	<AutocompleteSelect
		multiple
		{form}
		createFromSelection={true}
		optionsEndpoint="filtering-labels"
		optionsLabelField="label"
		field="filtering_labels"
		helpText={m.labelsHelpText()}
		label={m.labels()}
		translateOptions={false}
		allowUserOptions="append"
	/>
	{#if displayIAMGroups}
		<FolderIAMGroupsSelect {form}/>
	{/if}
{/if}
