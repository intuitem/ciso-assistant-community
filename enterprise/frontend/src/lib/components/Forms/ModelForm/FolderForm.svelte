<script lang="ts">
	import { page } from '$app/stores';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import type { SuperValidated } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Checkbox from '../Checkbox.svelte';
	import FileInput from '../FileInput.svelte';

	interface Props {
		form: SuperValidated<any>;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		importFolder?: boolean;
		object?: any;
		model: ModelInfo;
	}

	let {
		form,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		importFolder = false,
		object = {},
		model
	}: Props = $props();

	const setCreateIamGroups = (value: boolean) => {
		form.form.update((currentData) => ({
			...currentData,
			create_iam_groups: value
		}));
	};

	const normalizeParentSelection = (selection: string | string[] | undefined) =>
		Array.isArray(selection) ? selection.at(-1) : selection;

	function handleParentFolderChange(value: string | string[] | undefined) {
		const selectedId = normalizeParentSelection(value);
		const rootFolderId = $page.data.user?.root_folder_id;
		if (!selectedId) {
			setCreateIamGroups(false);
			return;
		}
		setCreateIamGroups(selectedId === rootFolderId);
	}
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
		{form}
		optionsEndpoint="folders?content_type=DO&content_type=GL"
		optionsSelf={object}
		field="parent_folder"
		pathField="path"
		cacheLock={cacheLocks['parent_folder']}
		bind:cachedValue={formDataCache['parent_folder']}
		label={m.parentDomain()}
		hide={initialData.parent_folder}
	/>
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
{/if}
