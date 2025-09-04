<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import Score from '$lib/components/Forms/Score.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { onMount } from 'svelte';
	import { run } from 'svelte/legacy';

	let displayCurrency = $state('€'); // Default to Euro

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		duplicate?: boolean;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		schema?: any;
		initialData?: Record<string, any>;
	}

	let {
		form,
		model,
		duplicate = false,
		cacheLocks = {},
		formDataCache = $bindable({}),
		schema = {},
		initialData = {}
	}: Props = $props();

	// Declare form store at top level
	const formStore = form.form;

	// Update currency when form data changes
	$effect(() => {
		const costData = $formStore.cost;
		if (costData?.currency) {
			displayCurrency = costData.currency;
		}
	});

	onMount(async () => {
		if (!model.selectOptions) {
			const selectOptions = {
				status: await fetch('/applied-controls/status').then((r) => r.json()),
				priority: await fetch('/applied-controls/priority').then((r) => r.json()),
				category: await fetch('/applied-controls/category').then((r) => r.json()),
				csf_function: await fetch('/applied-controls/csf_function').then((r) => r.json()),
				effort: await fetch('/applied-controls/effort').then((r) => r.json())
			};
			model.selectOptions = selectOptions;
		}
	});

	run(() => {
		if (model?.selectOptions?.priority) {
			model.selectOptions.priority.forEach((element) => {
				element.value = parseInt(element.value);
			});
		}
	});
</script>

{#if !duplicate}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="users?is_third_party=false"
		optionsLabelField="email"
		field="owner"
		cacheLock={cacheLocks['owner']}
		bind:cachedValue={formDataCache['owner']}
		label={m.owner()}
	/>
	<Select
		{form}
		options={model.selectOptions?.status}
		disableDoubleDash={true}
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
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="evidences"
		optionsExtraFields={[['folder', 'str']]}
		field="evidences"
		cacheLock={cacheLocks['evidences']}
		bind:cachedValue={formDataCache['evidences']}
		label={m.evidences()}
	/>

	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-tasks"
		header={m.projectManagement()}
	>
		<TextField
			{form}
			field="ref_id"
			label={m.refId()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<Select
			{form}
			options={model.selectOptions?.priority}
			field="priority"
			label={m.priority()}
			cacheLock={cacheLocks['priority']}
			bind:cachedValue={formDataCache['priority']}
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
			options={model.selectOptions?.effort}
			field="effort"
			label={m.effort()}
			helpText={m.effortHelpText()}
			cacheLock={cacheLocks['effort']}
			bind:cachedValue={formDataCache['effort']}
		/>
		<Select
			{form}
			options={model.selectOptions?.control_impact}
			field="control_impact"
			label={m.controlImpact()}
			helpText={m.impactHelpText()}
			cacheLock={cacheLocks['control_impact']}
			bind:cachedValue={formDataCache['control_impact']}
		/>
		<MarkdownField
			{form}
			field="observation"
			label={m.observation()}
			helpText={m.observationHelpText()}
			cacheLock={cacheLocks['observation']}
			bind:cachedValue={formDataCache['observation']}
		/>
	</Dropdown>

	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-money-bill-1"
		header={m.cost()}
	>
		<!-- Build Costs -->
		<div class="space-y-2">
			<h5 class="font-medium text-gray-600 my-2 py-2">{m.buildCosts()}</h5>
			<div class="grid grid-cols-2 gap-4">
				<NumberField
					{form}
					field="cost.build.fixed_cost"
					label="{m.fixedCost()} ({displayCurrency})"
					helpText={m.oneTimeImplementationCost()}
					min={0}
					step={1}
				/>
				<NumberField
					{form}
					field="cost.build.people_days"
					label={m.peopleDays()}
					helpText={m.implementationHelpText()}
					min={0}
					step={0.5}
				/>
				<!-- Amortization Period -->
				<NumberField
					{form}
					field="cost.amortization_period"
					label={m.amortizationPeriod()}
					helpText={m.amortizationPeriodHelpText()}
					min={1}
					max={50}
					step={1}
				/>
			</div>
		</div>

		<!-- Run Costs -->
		<div class="space-y-2">
			<h5 class="font-medium text-gray-600 my-2 py-2">{m.runCosts()}</h5>
			<div class="grid grid-cols-2 gap-4">
				<NumberField
					{form}
					field="cost.run.fixed_cost"
					label="{m.fixedCost()} ({displayCurrency})"
					helpText={m.annualOperationalCost()}
					min={0}
					step={1}
				/>
				<NumberField
					{form}
					field="cost.run.people_days"
					label={m.peopleDays()}
					helpText={m.annualManDaysHelpText()}
					min={0}
					step={0.5}
				/>
			</div>
		</div>
	</Dropdown>

	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-project-diagram"
		header={m.relationships()}
	>
		{#if schema.shape.category}
			<Select
				{form}
				options={model.selectOptions?.category}
				field="category"
				label={m.category()}
				cacheLock={cacheLocks['category']}
				bind:cachedValue={formDataCache['category']}
			/>
		{/if}
		<Select
			{form}
			options={model.selectOptions?.csf_function}
			field="csf_function"
			label={m.csfFunction()}
			cacheLock={cacheLocks['csf_function']}
			bind:cachedValue={formDataCache['csf_function']}
		/>
		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="assets"
			optionsExtraFields={[['folder', 'str']]}
			optionsInfoFields={{
				fields: [
					{
						field: 'type'
					}
				],
				classes: 'text-blue-500'
			}}
			field="assets"
			cacheLock={cacheLocks['assets']}
			bind:cachedValue={formDataCache['assets']}
			label={m.assets()}
		/>
		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="organisation-objectives"
			optionsExtraFields={[['folder', 'str']]}
			field="objectives"
			cacheLock={cacheLocks['objectives']}
			bind:cachedValue={formDataCache['objectives']}
			label={m.objectives()}
		/>
		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="security-exceptions"
			optionsExtraFields={[['folder', 'str']]}
			field="security_exceptions"
			cacheLock={cacheLocks['security_exceptions']}
			bind:cachedValue={formDataCache['security_exceptions']}
			label={m.securityExceptions()}
		/>
		<AutocompleteSelect
			multiple
			{form}
			createFromSelection={true}
			optionsEndpoint="filtering-labels"
			translateOptions={false}
			optionsLabelField="label"
			field="filtering_labels"
			helpText={m.labelsHelpText()}
			label={m.labels()}
			allowUserOptions="append"
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
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
