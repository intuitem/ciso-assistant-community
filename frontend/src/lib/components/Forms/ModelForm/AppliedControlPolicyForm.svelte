<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import Score from '$lib/components/Forms/Score.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let duplicate: boolean = false;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let schema: any = {};
	export let initialData: Record<string, any> = {};

	if (model.selectOptions && 'priority' in model.selectOptions) {
		model.selectOptions['priority'].forEach((element) => {
			element.value = parseInt(element.value);
		});
	}
</script>

{#if !duplicate}
	<AutocompleteSelect
		{form}
		multiple
		options={getOptions({ objects: model.foreignKeys['owner'], label: 'email' })}
		field="owner"
		cacheLock={cacheLocks['owner']}
		bind:cachedValue={formDataCache['owner']}
		label={m.owner()}
	/>
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<Score
		{form}
		label={m.progress()}
		field="progress_field"
		fullDonut
		min_score={0}
		max_score={100}
	/>
	<TextField
		type="date"
		{form}
		field="eta"
		label={m.eta()}
		helpText={m.etaHelpText()}
		cacheLock={cacheLocks['eta']}
		bind:cachedValue={formDataCache['eta']}
	/>
	<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
		<TextField
			{form}
			field="ref_id"
			label={m.refId()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<Select
			{form}
			options={model.selectOptions['priority']}
			field="priority"
			label={m.priority()}
			cacheLock={cacheLocks['priority']}
			bind:cachedValue={formDataCache['priority']}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({
				objects: model.foreignKeys['evidences'],
				extra_fields: [['folder', 'str']]
			})}
			field="evidences"
			cacheLock={cacheLocks['evidences']}
			bind:cachedValue={formDataCache['evidences']}
			label={m.evidences()}
		/>
		{#if schema.shape.category}
			<Select
				{form}
				options={model.selectOptions['category']}
				field="category"
				label={m.category()}
				cacheLock={cacheLocks['category']}
				bind:cachedValue={formDataCache['category']}
			/>
		{/if}
		<Select
			{form}
			options={model.selectOptions['csf_function']}
			field="csf_function"
			label={m.csfFunction()}
			cacheLock={cacheLocks['csf_function']}
			bind:cachedValue={formDataCache['csf_function']}
		/>
		<TextField
			type="date"
			{form}
			field="start_date"
			label={m.startDate()}
			helpText={m.startDateHelpText()}
			cacheLock={cacheLocks['start_date']}
			bind:cachedValue={formDataCache['start_date']}
		/>
		<TextField
			type="date"
			{form}
			field="expiry_date"
			label={m.expiryDate()}
			helpText={m.expiryDateHelpText()}
			cacheLock={cacheLocks['expiry_date']}
			bind:cachedValue={formDataCache['expiry_date']}
		/>
		<Select
			{form}
			options={model.selectOptions['effort']}
			field="effort"
			label={m.effort()}
			helpText={m.effortHelpText()}
			cacheLock={cacheLocks['effort']}
			bind:cachedValue={formDataCache['effort']}
		/>
		<NumberField
			{form}
			field="cost"
			label={m.cost()}
			helpText={m.costHelpText()}
			cacheLock={cacheLocks['cost']}
			bind:cachedValue={formDataCache['cost']}
		/>
		<TextField
			{form}
			field="link"
			label={m.link()}
			helpText={m.linkHelpText()}
			cacheLock={cacheLocks['link']}
			bind:cachedValue={formDataCache['link']}
		/>
	</Dropdown>
{/if}

{#if duplicate}
	<Checkbox
		{form}
		field="duplicate_evidences"
		label={m.bringTheEvidences()}
		helpText={m.bringTheEvidencesHelpText()}
	/>
{/if}

<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['folder'] })}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
