<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
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
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		object = {},
		debug = false
	}: Props = $props();
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
				<strong>initialData:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(initialData, null, 2)}</pre>
			</div>
			<div>
				<strong>formDataCache:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(formDataCache, null, 2)}</pre>
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
