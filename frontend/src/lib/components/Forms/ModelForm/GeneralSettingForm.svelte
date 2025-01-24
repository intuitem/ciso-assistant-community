<script lang="ts">
	import Select from '../Select.svelte';
	import NumberField from '../NumberField.svelte';
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
<NumberField
	{form}
	field="ebios_radar_max"
	label={"max"}
	cacheLock={cacheLocks['ebios_radar_max']}
	bind:cachedValue={formDataCache['ebios_radar_max']}
/>
<NumberField
	{form}
	field="ebios_radar_green_zone_radius"
	label={"green"}
	step={0.1}
	cacheLock={cacheLocks['ebios_radar_green_zone_radius']}
	bind:cachedValue={formDataCache['ebios_radar_green_zone_radius']}
/>
<NumberField
	{form}
	field="ebios_radar_yellow_zone_radius"
	label={"yellow"}
	step={0.1}
	cacheLock={cacheLocks['ebios_radar_yellow_zone_radius']}
	bind:cachedValue={formDataCache['ebios_radar_yellow_zone_radius']}
/>
<NumberField
	{form}
	field="ebios_radar_red_zone_radius"
	label={"red"}
	step={0.1}
	cacheLock={cacheLocks['ebios_radar_red_zone_radius']}
	bind:cachedValue={formDataCache['ebios_radar_red_zone_radius']}
/>
