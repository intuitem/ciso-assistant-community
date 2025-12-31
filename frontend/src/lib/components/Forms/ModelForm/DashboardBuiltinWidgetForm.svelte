<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
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
	const { value: chartTypeValue } = formFieldProxy(form, 'chart_type');

	// State for builtin metric options
	let selectedModel = $state<string>(object?.target_content_type_display || '');
	let selectedMetricKey = $state<string>(object?.metric_key || '');
	let availableMetrics = $state<Array<{ value: string; label: string; chart_types: string[] }>>([]);
	let selectedChartType = $state<string>(object?.chart_type || '');

	// Initialize formDataCache from object for edit mode
	$effect(() => {
		if (object?.time_range && !formDataCache['time_range']) {
			formDataCache['time_range'] = object.time_range;
		}
		if (object?.aggregation && !formDataCache['aggregation']) {
			formDataCache['aggregation'] = object.aggregation;
		}
	});

	// Chart type labels for display
	const chartTypeLabels: Record<string, string> = {
		kpi_card: 'KPI Card',
		gauge: 'Gauge',
		sparkline: 'Sparkline',
		line: 'Line',
		area: 'Area',
		bar: 'Bar',
		donut: 'Donut',
		pie: 'Pie',
		table: 'Table'
	};

	// Get available chart types based on selected metric
	const availableChartTypes = $derived.by(() => {
		if (!selectedMetricKey || availableMetrics.length === 0) {
			return [];
		}
		const metric = availableMetrics.find((m) => m.value === selectedMetricKey);
		if (!metric) return [];
		return metric.chart_types.map((ct) => ({
			value: ct,
			label: chartTypeLabels[ct] || ct
		}));
	});

	// Update available metrics when model selection changes
	$effect(() => {
		if (selectedModel && supportedModels[selectedModel]) {
			const metrics = Object.entries(supportedModels[selectedModel]).map(
				([key, meta]: [string, any]) => ({
					value: key,
					label: meta.label,
					chart_types: meta.chart_types || []
				})
			);
			availableMetrics = metrics;
			// Set first metric as default if none selected or current selection is invalid
			if (
				metrics.length > 0 &&
				(!selectedMetricKey || !metrics.find((m) => m.value === selectedMetricKey))
			) {
				selectedMetricKey = metrics[0].value;
			}
		} else {
			availableMetrics = [];
			selectedMetricKey = '';
		}
	});

	// Update chart type when metric changes (select first valid option)
	$effect(() => {
		if (availableChartTypes.length > 0) {
			// If current chart type is not valid for this metric, select the first valid one
			if (!availableChartTypes.find((ct) => ct.value === selectedChartType)) {
				selectedChartType = availableChartTypes[0].value;
			}
		}
	});

	// Set default model on mount if none selected
	$effect(() => {
		const modelNames = Object.keys(supportedModels);
		if (modelNames.length > 0 && !selectedModel) {
			selectedModel = modelNames[0];
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

	// Sync chart type to formDataCache and form field
	$effect(() => {
		if (selectedChartType) {
			formDataCache['chart_type'] = selectedChartType;
			$chartTypeValue = selectedChartType;
		}
	});

	// Map model names to translation keys
	const modelTranslationKeys: Record<string, () => string> = {
		ComplianceAssessment: m.complianceAssessment,
		RiskAssessment: m.riskAssessment,
		FindingsAssessment: m.findingsAssessment,
		Folder: m.domain
	};

	// Model options for the select dropdown
	const modelOptions = $derived(
		Object.keys(supportedModels).map((name) => ({
			value: name,
			label: modelTranslationKeys[name]?.() || name
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
				<strong>object:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(object, null, 2)}</pre>
			</div>
			<div>
				<strong>supportedModels:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(supportedModels, null, 2)}</pre>
			</div>
			<div>
				<strong>availableChartTypes:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(availableChartTypes, null, 2)}</pre>
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

<!-- Builtin Metric Selection -->
<div class="space-y-4">
	<!-- Hidden field to send target_model to backend -->
	<input type="hidden" name="target_model" value={selectedModel} />

	<div>
		<label class="text-sm font-semibold" for="target_model_select">{m.targetObjectType()}</label>
		<select id="target_model_select" class="select" bind:value={selectedModel}>
			{#each modelOptions as option}
				<option value={option.value}>{option.label}</option>
			{/each}
		</select>
	</div>

	{#if selectedModel && targetObjectEndpoint}
		{#key selectedModel}
			<AutocompleteSelect
				{form}
				optionsEndpoint={targetObjectEndpoint}
				optionsLabelField="auto"
				field="target_object_id"
				cacheLock={cacheLocks['target_object_id']}
				bind:cachedValue={formDataCache['target_object_id']}
				label={m.targetObject()}
				optionsInfoFields={selectedModel === 'Folder'
					? undefined
					: {
							fields: [
								{ field: 'version', translate: true },
								{ field: 'perimeter', path: 'str', translate: false },
								{ field: 'status', translate: true }
							],
							position: 'suffix',
							separator: ' • ',
							classes: 'text-surface-500'
						}}
			/>
		{/key}
	{/if}

	{#if availableMetrics.length > 0}
		<div>
			<label class="text-sm font-semibold" for="metric_key">{m.metric()}</label>
			<select id="metric_key" name="metric_key" class="select" bind:value={selectedMetricKey}>
				{#each availableMetrics as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
		</div>
	{/if}
</div>

<TextField
	{form}
	field="title"
	label={m.widgetTitle()}
	cacheLock={cacheLocks['title']}
	bind:cachedValue={formDataCache['title']}
/>

<div class="grid grid-cols-2 gap-4">
	<div>
		<label class="text-sm font-semibold" for="chart_type">{m.chartType()}</label>
		<select
			id="chart_type"
			name="chart_type"
			class="select"
			bind:value={selectedChartType}
			disabled={availableChartTypes.length === 0}
		>
			{#each availableChartTypes as option}
				<option value={option.value}>{option.label}</option>
			{/each}
		</select>
	</div>

	{#if model.selectOptions?.['time_range']}
		<div>
			<label class="text-sm font-semibold" for="time_range">{m.timeRange()}</label>
			<select
				id="time_range"
				name="time_range"
				class="select"
				bind:value={formDataCache['time_range']}
			>
				{#each model.selectOptions['time_range'] as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
		</div>
	{/if}
</div>

<!-- Aggregation hidden for now -->
<input type="hidden" name="aggregation" value={formDataCache['aggregation'] || 'none'} />

<Checkbox
	{form}
	field="show_target"
	label={m.showTarget()}
	cacheLock={cacheLocks['show_target']}
	bind:cachedValue={formDataCache['show_target']}
/>
