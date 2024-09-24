<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
</script>

<AutocompleteSelect
	{form}
	options={getOptions({
		objects: model.foreignKeys['risk_assessment'],
		label: 'str',
		extra_fields: [['project', 'str']]
	})}
	field="risk_assessment"
	cacheLock={cacheLocks['risk_assessment']}
	bind:cachedValue={formDataCache['risk_assessment']}
	label={m.riskAssessment()}
	hidden={initialData.risk_assessment}
/>
<AutocompleteSelect
	{form}
	multiple
	options={getOptions({
		objects: model.foreignKeys['threats'],
		extra_fields: [['folder', 'str']],
		label: 'auto'
	})}
	field="threats"
	cacheLock={cacheLocks['threats']}
	bind:cachedValue={formDataCache['threats']}
	label={m.threats()}
/>
