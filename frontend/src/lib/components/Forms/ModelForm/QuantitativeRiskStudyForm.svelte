<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { onMount } from 'svelte';

	let displayCurrency = $state('€'); // Default to Euro

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		duplicate?: boolean;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
		context?: string;
	}

	let {
		form,
		model,
		duplicate = false,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = 'default'
	}: Props = $props();

	// Declare form store at top level
	const formStore = form.form;

	// Fetch currency from global settings
	onMount(async () => {
		try {
			const response = await fetch('/global-settings');
			if (response.ok) {
				const globalSettings = await response.json();
				const generalSetting = globalSettings.results?.find(
					(setting: any) => setting.name === 'general'
				);
				if (generalSetting?.value?.currency) {
					displayCurrency = generalSetting.value.currency;
				}
			}
		} catch (error) {
			console.warn('Could not fetch global settings for currency:', error);
		}
	});
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="authors"
	cacheLock={cacheLocks['authors']}
	bind:cachedValue={formDataCache['authors']}
	label={m.authors()}
/>
{#if !duplicate}
	<Select
		{form}
		options={model.selectOptions['status']}
		translateOptions={false}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>

	<Select
		{form}
		options={model.selectOptions['distribution_model']}
		disableDoubleDash
		translateOptions={false}
		field="distribution_model"
		label="Distribution Model"
		disabled
		cacheLock={cacheLocks['distribution_model']}
		bind:cachedValue={formDataCache['distribution_model']}
	/>

	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-bullseye"
		header="Tolerance settings"
	>
		<NumberField
			{form}
			field="loss_threshold"
			label="{m.lossThreshold()} ({displayCurrency})"
			min={0}
			step={1}
			helpText={m.lossThresholdHelpText()}
			cacheLock={cacheLocks['loss_threshold']}
			bind:cachedValue={formDataCache['loss_threshold']}
		/>

		<div class="space-y-2">
			<h5 class="font-medium text-gray-600 my-2 py-2">Risk Tolerance Points</h5>
			<div class="grid grid-cols-2 gap-4">
				<NumberField
					{form}
					field="risk_tolerance.points.point1.probability"
					label="Point 1 - Probability"
					min={0.01}
					max={0.99}
					step={0.01}
					helpText="Probability value (0.01-0.99). You can start with 0.99 for the most frequent acceptable issues"
				/>
				<NumberField
					{form}
					field="risk_tolerance.points.point1.acceptable_loss"
					label="Point 1 - Tolerable Loss ({displayCurrency})"
					min={1}
					step={1}
					helpText="Acceptable loss amount for point 1"
				/>
			</div>
			<div class="grid grid-cols-2 gap-4">
				<NumberField
					{form}
					field="risk_tolerance.points.point2.probability"
					label="Point 2 - Probability"
					min={0.01}
					max={0.99}
					step={0.01}
					helpText="Probability value (0.01-0.99), You can close with 0.01 for the most rare acceptable cases"
				/>
				<NumberField
					{form}
					field="risk_tolerance.points.point2.acceptable_loss"
					label="Point 2 - Tolerable Loss ({displayCurrency})"
					min={1}
					step={1}
					helpText="Acceptable loss amount for point 2"
				/>
			</div>
		</div>
	</Dropdown>

	<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="users?is_third_party=false"
			optionsLabelField="email"
			field="reviewers"
			cacheLock={cacheLocks['reviewers']}
			bind:cachedValue={formDataCache['reviewers']}
			label={m.reviewers()}
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

		<TextField
			type="date"
			{form}
			field="due_date"
			label={m.dueDate()}
			helpText={m.dueDateHelpText()}
			cacheLock={cacheLocks['due_date']}
			bind:cachedValue={formDataCache['due_date']}
		/>

		<MarkdownField
			{form}
			field="observation"
			label={m.observation()}
			cacheLock={cacheLocks['observation']}
			bind:cachedValue={formDataCache['observation']}
		/>
	</Dropdown>
{/if}
