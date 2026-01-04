<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Duration from '../Duration.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
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

	// export let updated_fields: Set<string> = new Set();
</script>

<Duration
	{form}
	field="point_in_time"
	label={m.pointInTime()}
	cacheLock={cacheLocks['point_in_time']}
	bind:cachedValue={formDataCache['point_in_time']}
	enabledUnits={['days', 'hours', 'minutes']}
/>
<AutocompleteSelect
	{form}
	field="asset_assessment"
	optionsEndpoint="asset-assessments"
	cacheLock={cacheLocks['asset_assessment']}
	bind:cachedValue={formDataCache['asset_assessment']}
	label={m.assetAssessment()}
	hidden={initialData.asset_assessment}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="terminologies?field_path=qualifications&is_visible=true"
	field="qualifications"
	optionsLabelField="translated_name"
	label={m.qualifications()}
/>
<Select
	{form}
	options={model.selectOptions['quali_impact']}
	field="quali_impact"
	label={m.impact()}
	cacheLock={cacheLocks['quali_impact']}
	bind:cachedValue={formDataCache['quali_impact']}
/>
<TextArea
	{form}
	field="justification"
	label={m.justification()}
	cacheLock={cacheLocks['justification']}
	bind:cachedValue={formDataCache['justification']}
/>
