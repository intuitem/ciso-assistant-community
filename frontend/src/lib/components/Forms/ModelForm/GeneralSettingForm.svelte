<script lang="ts">
	import Select from '../Select.svelte';
	import * as m from '$paraglide/messages';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';

	export let form: SuperForm<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
</script>

<Select
	{form}
	field="security_objective_scale"
	cacheLock={cacheLocks['security_objective_scale']}
	bind:cachedValue={formDataCache['security_objective_scale']}
	options={model.selectOptions['security_objective_scale']}
	helpText={m.securityObjectiveScaleHelpText()}
	label={m.securityObjectiveScale()}
/>
