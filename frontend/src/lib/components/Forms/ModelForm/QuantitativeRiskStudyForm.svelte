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
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	let displayCurrency = $derived(page.data?.settings?.currency ?? '€'); // Default to Euro

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

	// Local state for percentage display (0-100) for tolerance points
	let point1ProbabilityPercent = $state<number | undefined>(undefined);
	let point2ProbabilityPercent = $state<number | undefined>(undefined);

	// Initialize percentages from existing form data on mount
	onMount(() => {
		const riskTolerance = $formStore.risk_tolerance;
		const point1Prob = riskTolerance?.points?.point1?.probability;
		const point2Prob = riskTolerance?.points?.point2?.probability;

		if (point1Prob !== undefined && point1Prob !== null && typeof point1Prob === 'number') {
			point1ProbabilityPercent = Math.round(point1Prob * 10000) / 100; // Convert 0-1 to 0-100
		}
		if (point2Prob !== undefined && point2Prob !== null && typeof point2Prob === 'number') {
			point2ProbabilityPercent = Math.round(point2Prob * 10000) / 100; // Convert 0-1 to 0-100
		}
	});

	// Sync percentage to probability when user changes the input
	function updatePoint1Probability() {
		// Ensure risk_tolerance structure exists
		if (!$formStore.risk_tolerance) {
			$formStore.risk_tolerance = { points: { point1: {}, point2: {} } };
		}
		if (!$formStore.risk_tolerance.points) {
			$formStore.risk_tolerance.points = { point1: {}, point2: {} };
		}
		if (!$formStore.risk_tolerance.points.point1) {
			$formStore.risk_tolerance.points.point1 = {};
		}

		if (
			point1ProbabilityPercent !== undefined &&
			point1ProbabilityPercent !== null &&
			typeof point1ProbabilityPercent === 'number'
		) {
			$formStore.risk_tolerance.points.point1.probability =
				Math.round(point1ProbabilityPercent * 100) / 10000; // Convert 0-100 to 0-1
		} else {
			$formStore.risk_tolerance.points.point1.probability = undefined;
		}
	}

	function updatePoint2Probability() {
		// Ensure risk_tolerance structure exists
		if (!$formStore.risk_tolerance) {
			$formStore.risk_tolerance = { points: { point1: {}, point2: {} } };
		}
		if (!$formStore.risk_tolerance.points) {
			$formStore.risk_tolerance.points = { point1: {}, point2: {} };
		}
		if (!$formStore.risk_tolerance.points.point2) {
			$formStore.risk_tolerance.points.point2 = {};
		}

		if (
			point2ProbabilityPercent !== undefined &&
			point2ProbabilityPercent !== null &&
			typeof point2ProbabilityPercent === 'number'
		) {
			$formStore.risk_tolerance.points.point2.probability =
				Math.round(point2ProbabilityPercent * 100) / 10000; // Convert 0-100 to 0-1
		} else {
			$formStore.risk_tolerance.points.point2.probability = undefined;
		}
	}
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
				<!-- Point 1 Probability as Percentage -->
				<div class="form-control">
					<label class="label" for="point1_probability_percent">
						<span class="label-text">Point 1 - Probability (%)</span>
					</label>
					<input
						type="number"
						id="point1_probability_percent"
						class="input input-bordered w-full"
						bind:value={point1ProbabilityPercent}
						oninput={updatePoint1Probability}
						step="0.1"
						min="1"
						max="99"
					/>
					<label class="label" for="point1_probability_percent">
						<span class="label-text-alt text-surface-500"
							>Probability percentage (1-99%). You can start with 99% for the most frequent
							acceptable issues</span
						>
					</label>
				</div>
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
				<!-- Point 2 Probability as Percentage -->
				<div class="form-control">
					<label class="label" for="point2_probability_percent">
						<span class="label-text">Point 2 - Probability (%)</span>
					</label>
					<input
						type="number"
						id="point2_probability_percent"
						class="input input-bordered w-full"
						bind:value={point2ProbabilityPercent}
						oninput={updatePoint2Probability}
						step="0.1"
						min="1"
						max="99"
					/>
					<label class="label" for="point2_probability_percent">
						<span class="label-text-alt text-surface-500"
							>Probability percentage (1-99%). You can close with 1% for the most rare acceptable
							cases</span
						>
					</label>
				</div>
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
