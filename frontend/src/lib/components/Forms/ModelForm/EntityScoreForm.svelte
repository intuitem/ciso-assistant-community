<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	const formData = form.form;

	let normalized = $derived(
		$formData.scale_max ? Math.round(($formData.score / $formData.scale_max) * 1000) / 10 : null
	);
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="terminologies"
	optionsDetailedUrlParameters={[
		['field_path', 'entity_score.provider'],
		['is_visible', 'true']
	]}
	field="provider"
	cacheLock={cacheLocks['provider']}
	bind:cachedValue={formDataCache['provider']}
	label={m.provider()}
	helpText={m.moreOnTerminologiesHelpText()}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="entities"
	field="entity"
	cacheLock={cacheLocks['entity']}
	bind:cachedValue={formDataCache['entity']}
	label={m.entity()}
	hidden={initialData.entity !== undefined}
/>
<div class="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_1fr_auto] items-start">
	<NumberField
		{form}
		field="score"
		label={m.score()}
		cacheLock={cacheLocks['score']}
		bind:cachedValue={formDataCache['score']}
	/>
	<NumberField
		{form}
		field="scale_max"
		label={m.scaleMaximum()}
		helpText={m.scaleMaximumHelpText()}
		cacheLock={cacheLocks['scale_max']}
		bind:cachedValue={formDataCache['scale_max']}
	/>
	<div class="flex flex-col">
		<span class="text-sm font-semibold whitespace-nowrap">{m.normalizedScore()}</span>
		<span class="chip text-base text-center px-4 py-1 mt-1 rounded-base preset-filled">
			{normalized ?? '--'}
		</span>
	</div>
</div>
<TextField
	type="date"
	{form}
	field="as_of"
	label={m.asOf()}
	helpText={m.asOfHelpText()}
	cacheLock={cacheLocks['as_of']}
	bind:cachedValue={formDataCache['as_of']}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-ellipsis" header={m.more()}>
	<TextField
		{form}
		field="grade"
		label={m.grade()}
		helpText={m.gradeHelpText()}
		cacheLock={cacheLocks['grade']}
		bind:cachedValue={formDataCache['grade']}
	/>
	<TextField
		{form}
		field="url"
		label={m.link()}
		helpText={m.linkHelpText()}
		cacheLock={cacheLocks['url']}
		bind:cachedValue={formDataCache['url']}
	/>
	<TextArea
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="filtering-labels"
		optionsLabelField="label"
		field="filtering_labels"
		helpText={m.labelsHelpText()}
		label={m.labels()}
		translateOptions={false}
		allowUserOptions="append"
		cacheLock={cacheLocks['filtering_labels']}
		bind:cachedValue={formDataCache['filtering_labels']}
	/>
</Dropdown>
