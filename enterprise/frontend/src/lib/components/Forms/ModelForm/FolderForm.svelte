<script lang="ts">
	import { onMount } from 'svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { safeTranslate } from '$lib/utils/i18n';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
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

	let viewableFromDescendantsHelpText = $state(
		m.viewableFromDescendantsHelpText({ stringified_model_names: '...' })
	);

	onMount(() => {
		const isEdit = Boolean(object?.id);
		if (!isEdit && form.data?.create_iam_groups !== true) {
			form.form.update((currentData) => ({
				...currentData,
				create_iam_groups: true
			}));
		}

		initViewableFromDescendantsHelpText();
	});

	async function initViewableFromDescendantsHelpText() {
		let stringifiedModelNames = m.anErrorOccurred();

		try {
			const req = await fetch('/content-types?may_be_viewable_from_descendants=true');

			if (req.ok) {
				const res = await req.json();
				const modelNames = res.map((model) => safeTranslate(model.label));

				stringifiedModelNames = modelNames.join(' | ');
			}
		} catch (error) {
			stringifiedModelNames = m.networkErrorWithMessage({ message: error?.message });
		}

		viewableFromDescendantsHelpText = m.viewableFromDescendantsHelpText({
			stringified_model_names: stringifiedModelNames
		});
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
	<Checkbox
		{form}
		field="create_missing_asset_classes"
		label={m.createMissingAssetClasses()}
		helpText={m.createMissingAssetClassesHelpText()}
	/>
{:else}
	<FolderTreeSelect
		{form}
		field="parent_folder"
		optionsSelf={object}
		cacheLock={cacheLocks['parent_folder']}
		bind:cachedValue={formDataCache['parent_folder']}
		label={m.parentDomain()}
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
	<Checkbox
		{form}
		field="create_iam_groups"
		label={m.createIamGroups()}
		helpText={m.whenEnabledIamGroupsAreCreatedAutomatically()}
	/>
	<Checkbox
		{form}
		field="viewable_from_descendants"
		label={m.viewableFromDescendants()}
		helpText={viewableFromDescendantsHelpText}
	/>
{/if}
