<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '#lib/components/Forms/TextField.svelte';
	import Checkbox from '#lib/components/Forms/Checkbox.svelte';
	import ThresholdsEditor from './ThresholdsEditor.svelte';
	import DashboardWidgetChart from '#lib/components/Chart/DashboardWidgetChart.svelte';
	import { formFieldProxy } from 'sveltekit-superforms';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '#lib/utils/types.js';
	import { m } from '#paraglide/messages.js';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		debug?: boolean;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		debug = false
	}: Props = $props();

	// The widget as it will look, drawn from the metric's recent values while
	// the options are picked.
	const { value: metricInstanceValue } = formFieldProxy(form, 'metric_instance');
	const { value: chartTypeValue } = formFieldProxy(form, 'chart_type');
	const { value: timeRangeValue } = formFieldProxy(form, 'time_range');
	const { value: showTargetValue } = formFieldProxy(form, 'show_target');
	const { value: titleValue } = formFieldProxy(form, 'title');
	const { value: widgetConfigValue } = formFieldProxy(form, 'widget_config');

	let pickedInstance = $state<any>(null);
	let samples = $state<any[]>([]);
	$effect(() => {
		const id = $metricInstanceValue;
		if (!id) {
			pickedInstance = null;
			samples = [];
			return;
		}
		// The previous metric's preview goes before the next one loads.
		pickedInstance = null;
		samples = [];
		let alive = true;
		Promise.all([
			fetch(`/fe-api/metrology/instance/${id}`).then((r) => (r.ok ? r.json() : null)),
			fetch(`/fe-api/metrology/samples/${id}`).then((r) => (r.ok ? r.json() : { results: [] }))
		])
			.then(([instance, data]) => {
				if (!alive) return;
				pickedInstance = instance;
				samples = Array.isArray(data) ? data : (data.results ?? []);
			})
			.catch(() => {
				if (alive) {
					pickedInstance = null;
					samples = [];
				}
			});
		return () => {
			alive = false;
		};
	});
	const previewWidget = $derived({
		id: 'preview',
		chart_type: $chartTypeValue || 'line',
		time_range: $timeRangeValue || '30d',
		show_target: !!$showTargetValue,
		title: $titleValue,
		widget_config: $widgetConfigValue ?? {},
		metric_instance: pickedInstance,
		is_custom_metric: true
	});
	const previewKey = $derived(
		`${previewWidget.chart_type}|${previewWidget.time_range}|${previewWidget.show_target}|${samples.length}|${JSON.stringify(previewWidget.widget_config)}`
	);
</script>

{#if debug}
	<div class="card bg-yellow-50 p-4 my-4 border-2 border-yellow-300">
		<h4 class="font-semibold mb-2">Debug Info:</h4>
		<div class="text-xs space-y-2">
			<div>
				<strong>object:</strong>
				<pre class="bg-surface-50-950 p-2 rounded mt-1">{JSON.stringify(object, null, 2)}</pre>
			</div>
			<div>
				<strong>initialData:</strong>
				<pre class="bg-surface-50-950 p-2 rounded mt-1">{JSON.stringify(initialData, null, 2)}</pre>
			</div>
			<div>
				<strong>formDataCache:</strong>
				<pre class="bg-surface-50-950 p-2 rounded mt-1">{JSON.stringify(
						formDataCache,
						null,
						2
					)}</pre>
			</div>
		</div>
	</div>
{/if}

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

<!-- Custom Metric Selection -->
<AutocompleteSelect
	{form}
	optionsEndpoint="metric-instances"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="metric_instance"
	cacheLock={cacheLocks['metric_instance']}
	bind:cachedValue={formDataCache['metric_instance']}
	label={m.metricInstance()}
/>

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
		disableDoubleDash={true}
	/>
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

<ThresholdsEditor {form} {object} chartType={formDataCache['chart_type'] ?? object?.chart_type} />

<div class="form-group rounded-base border border-surface-200-800 p-3" data-testid="widget-preview">
	<span class="text-sm font-semibold block">{m.widgetPreview()}</span>
	<p class="text-xs text-surface-500 mb-2">{m.widgetPreviewHelpText()}</p>
	{#if pickedInstance}
		<div class="h-64 flex flex-col">
			{#key previewKey}
				<DashboardWidgetChart widget={previewWidget} {samples} />
			{/key}
		</div>
	{:else}
		<p class="text-sm text-surface-500 m-0">{m.pickAMetricToPreview()}</p>
	{/if}
</div>
