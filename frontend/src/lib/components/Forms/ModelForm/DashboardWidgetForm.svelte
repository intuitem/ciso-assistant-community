<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import { formFieldProxy, type SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		data?: any;
		object?: any;
		debug?: boolean;
		supportedModels?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		object = {},
		debug = false,
		supportedModels = {}
	}: Props = $props();

	// Get form field proxies for the builtin metric fields
	const { value: targetModelValue } = formFieldProxy(form, 'target_model');
	const { value: metricKeyValue } = formFieldProxy(form, 'metric_key');

	// State for metric type selection
	let metricType = $state<'custom' | 'builtin'>(
		object?.target_content_type ? 'builtin' : 'custom'
	);

	// State for builtin metric options - use local state for UI
	let selectedModel = $state<string>(object?.target_content_type_display || '');
	let selectedMetricKey = $state<string>(object?.metric_key || '');
	let availableMetrics = $state<Array<{ value: string; label: string }>>([]);

	// Track previous metric type to only clear on actual changes
	let previousMetricType = $state<'custom' | 'builtin' | null>(null);

	// Update available metrics when model selection changes
	$effect(() => {
		if (selectedModel && supportedModels[selectedModel]) {
			availableMetrics = Object.entries(supportedModels[selectedModel]).map(
				([key, meta]: [string, any]) => ({
					value: key,
					label: meta.label
				})
			);
		} else {
			availableMetrics = [];
		}
	});

	// Sync selectedModel to form field for submission
	$effect(() => {
		$targetModelValue = selectedModel || null;
	});

	// Sync selectedMetricKey to form field for submission
	$effect(() => {
		$metricKeyValue = selectedMetricKey || null;
	});

	// Clear conflicting fields when metric type changes (but not on initial load)
	$effect(() => {
		if (previousMetricType !== null && previousMetricType !== metricType) {
			if (metricType === 'custom') {
				// Clear builtin fields when switching to custom
				selectedModel = '';
				selectedMetricKey = '';
				$targetModelValue = null;
				$metricKeyValue = null;
				formDataCache['target_object_id'] = undefined;
			} else {
				// Clear custom field when switching to builtin
				formDataCache['metric_instance'] = undefined;
			}
		}
		previousMetricType = metricType;
	});

	// Model options for the select dropdown
	const modelOptions = $derived(
		Object.keys(supportedModels).map((name) => ({
			value: name,
			label: name.replace(/([A-Z])/g, ' $1').trim() // Add spaces before capitals
		}))
	);

	// Endpoint for target object selection based on selected model
	const targetObjectEndpoint = $derived.by(() => {
		switch (selectedModel) {
			case 'ComplianceAssessment':
				return 'compliance-assessments';
			case 'RiskAssessment':
				return 'risk-assessments';
			case 'FindingsAssessment':
				return 'findings-assessments';
			case 'Folder':
				return 'folders?content_type=DO';
			default:
				return '';
		}
	});
</script>

{#if debug}
	<div class="card bg-yellow-50 p-4 my-4 border-2 border-yellow-300">
		<h4 class="font-semibold mb-2">Debug Info:</h4>
		<div class="text-xs space-y-2">
			<div>
				<strong>initialData:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(initialData, null, 2)}</pre>
			</div>
			<div>
				<strong>formDataCache:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(formDataCache, null, 2)}</pre>
			</div>
			<div>
				<strong>supportedModels:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(supportedModels, null, 2)}</pre>
			</div>
			<div>
				<strong>modelOptions:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(modelOptions, null, 2)}</pre>
			</div>
		</div>
	</div>
{/if}

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="dashboards"
	optionsLabelField="name"
	field="dashboard"
	cacheLock={cacheLocks['dashboard']}
	bind:cachedValue={formDataCache['dashboard']}
	label={m.dashboard()}
	hidden={!!initialData.dashboard}
	disabled={!!initialData.dashboard}
/>

<!-- Metric Type Selection -->
<div class="space-y-2">
	<label class="label">
		<span>{m.metricType()}</span>
	</label>
	<div class="flex gap-4">
		<label class="flex items-center gap-2 cursor-pointer">
			<input
				type="radio"
				name="metric_type"
				value="custom"
				bind:group={metricType}
				class="radio"
			/>
			<span>{m.customMetric()}</span>
		</label>
		<label class="flex items-center gap-2 cursor-pointer">
			<input
				type="radio"
				name="metric_type"
				value="builtin"
				bind:group={metricType}
				class="radio"
			/>
			<span>{m.builtinMetric()}</span>
		</label>
	</div>
</div>

{#if metricType === 'custom'}
	<!-- Custom Metric Selection -->
	<AutocompleteSelect
		{form}
		optionsEndpoint="metric-instances"
		optionsLabelField="auto"
		field="metric_instance"
		cacheLock={cacheLocks['metric_instance']}
		bind:cachedValue={formDataCache['metric_instance']}
		label={m.metricInstance()}
	/>
{:else}
	<!-- Builtin Metric Selection -->
	<div class="space-y-4">
		<!-- Hidden field to send target_model to backend -->
		<input type="hidden" name="target_model" value={selectedModel} />

		<div>
			<label class="text-sm font-semibold" for="target_model_select">{m.targetObjectType()}</label>
			<select
				id="target_model_select"
				class="select"
				bind:value={selectedModel}
			>
				<option value="">--</option>
				{#each modelOptions as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
		</div>

		{#if selectedModel && targetObjectEndpoint}
			<AutocompleteSelect
				{form}
				optionsEndpoint={targetObjectEndpoint}
				optionsLabelField="auto"
				field="target_object_id"
				cacheLock={cacheLocks['target_object_id']}
				bind:cachedValue={formDataCache['target_object_id']}
				label={m.targetObject()}
			/>
		{/if}

		{#if availableMetrics.length > 0}
			<div>
				<label class="text-sm font-semibold" for="metric_key">{m.metric()}</label>
				<select
					id="metric_key"
					name="metric_key"
					class="select"
					bind:value={selectedMetricKey}
				>
					<option value="">--</option>
					{#each availableMetrics as option}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>
			</div>
		{/if}
	</div>
{/if}

<TextField
	{form}
	field="title"
	label={m.widgetTitle()}
	cacheLock={cacheLocks['title']}
	bind:cachedValue={formDataCache['title']}
/>

<div class="grid grid-cols-2 gap-4">
	<Select
		{form}
		options={model.selectOptions['chart_type']}
		field="chart_type"
		cacheLock={cacheLocks['chart_type']}
		bind:cachedValue={formDataCache['chart_type']}
		label={m.chartType()}
		disableDoubleDash={true}
	/>
	<Select
		{form}
		options={model.selectOptions['time_range']}
		field="time_range"
		cacheLock={cacheLocks['time_range']}
		bind:cachedValue={formDataCache['time_range']}
		label={m.timeRange()}
	/>
</div>

<!-- Aggregation hidden for now -->
<input type="hidden" name="aggregation" value={formDataCache['aggregation'] || 'none'} />

<div class="flex flex-wrap gap-4">
	<Checkbox
		{form}
		field="show_target"
		label={m.showTarget()}
		cacheLock={cacheLocks['show_target']}
		bind:cachedValue={formDataCache['show_target']}
	/>
	<Checkbox
		{form}
		field="show_legend"
		label={m.showLegend()}
		cacheLock={cacheLocks['show_legend']}
		bind:cachedValue={formDataCache['show_legend']}
	/>
</div>
