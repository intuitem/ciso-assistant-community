<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		duplicate?: boolean;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>; // export let context: string = 'default';
	}

	let {
		form,
		model,
		duplicate = false,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	let isLocked = $derived(form.data?.is_locked || object?.is_locked || false);

	let selectedFolder = $state<string | undefined>(undefined);
	let folderKey = $state(0);
	let isAutoFillingFolder = $state(false);

	function handleFolderChange(folderId: string) {
		selectedFolder = folderId;
		// Clear perimeter when folder changes (unless we're auto-filling from perimeter)
		if (!isAutoFillingFolder && form.data?.perimeter) {
			form.form.update((currentData) => ({
				...currentData,
				perimeter: undefined
			}));
		}
		isAutoFillingFolder = false;
	}

	async function handlePerimeterChange(perimeterId: string) {
		if (perimeterId && !selectedFolder) {
			// Fetch perimeter to get its folder and auto-fill
			try {
				const response = await fetch(`/perimeters/${perimeterId}`);
				if (response.ok) {
					const perimeter = await response.json();
					if (perimeter.folder?.id) {
						isAutoFillingFolder = true;
						selectedFolder = perimeter.folder.id;
						// Update form data and force folder component to re-render
						form.form.update((currentData) => ({
							...currentData,
							folder: perimeter.folder.id
						}));
						folderKey++;
					}
				}
			} catch (error) {
				console.error('Error fetching perimeter:', error);
			}
		}
	}

	// export let updated_fields: Set<string> = new Set();
</script>

{#key folderKey}
	<AutocompleteSelect
		{form}
		optionsEndpoint="folders?content_type=DO&content_type=GL"
		field="folder"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.folder()}
		onChange={handleFolderChange}
		mount={handleFolderChange}
	/>
{/key}
{#key selectedFolder}
	<AutocompleteSelect
		{form}
		optionsEndpoint="perimeters"
		optionsDetailedUrlParameters={selectedFolder ? [['folder', selectedFolder]] : []}
		optionsExtraFields={[['folder', 'str']]}
		field="perimeter"
		nullable
		cacheLock={cacheLocks['perimeter']}
		bind:cachedValue={formDataCache['perimeter']}
		label={m.perimeter()}
		onChange={handlePerimeterChange}
	/>
{/key}
<TextField
	{form}
	field="version"
	label={m.version()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	hide
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<AutocompleteSelect
	{form}
	disabled={object.id}
	optionsEndpoint="risk-matrices"
	field="risk_matrix"
	cacheLock={cacheLocks['risk_matrix']}
	bind:cachedValue={formDataCache['risk_matrix']}
	label={m.riskMatrix()}
	helpText={m.riskAssessmentMatrixHelpText()}
	hidden={initialData.risk_matrix}
/>
<TextField
	type="date"
	{form}
	field="due_date"
	label={m.dueDate()}
	helpText={m.dueDateHelpText()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="authors"
	cacheLock={cacheLocks['authors']}
	bind:cachedValue={formDataCache['authors']}
	label={m.authors()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="reviewers"
	cacheLock={cacheLocks['reviewers']}
	bind:cachedValue={formDataCache['reviewers']}
	label={m.reviewers()}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	{#if !page.data.user.is_third_party}
		<Checkbox
			{form}
			field="is_locked"
			label={m.isLocked()}
			helpText={m.isLockedHelpText()}
			cacheLock={cacheLocks['is_locked']}
			bind:cachedValue={formDataCache['is_locked']}
		/>
	{/if}
</Dropdown>
