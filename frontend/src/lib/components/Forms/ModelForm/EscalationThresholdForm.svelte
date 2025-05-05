<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let duplicate: boolean = false;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: Record<string, any> = {};
	// export let context: string = 'default';
	// export let updated_fields: Set<string> = new Set();
</script>

<NumberField
	{form}
	field="point_in_time"
	label={m.pointInTime()}
	cacheLock={cacheLocks['point_in_time']}
	bind:cachedValue={formDataCache['point_in_time']}
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
<TextArea
	{form}
	field="rationale"
	label={m.rationale()}
	cacheLock={cacheLocks['rationale']}
	bind:cachedValue={formDataCache['rationale']}
/>
