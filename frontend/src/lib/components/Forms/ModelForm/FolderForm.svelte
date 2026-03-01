<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import FileInput from '../FileInput.svelte';
	import Checkbox from '../Checkbox.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';

	// Props unused but referenced to avoid browser warnings because they're needed for enterprise Folderform

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

	let {
		form,
		importFolder = false,
		cacheLocks = {},
		formDataCache = {},
		initialData = {},
		object = {},
		model
	}: Props = $props();

	onMount(() => {
		const isEdit = Boolean(object?.id);
		if (!isEdit && form.data?.create_iam_groups !== true) {
			form.form.update((currentData) => ({
				...currentData,
				create_iam_groups: true
			}));
		}
	});
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
	<Checkbox
		{form}
		field="create_iam_groups"
		label={m.createIamGroups()}
		helpText={m.whenEnabledIamGroupsAreCreatedAutomatically()}
	/>
{/if}
