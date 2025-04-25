<script lang="ts">
	import Select from '../Select.svelte';
	import NumberField from '../NumberField.svelte';
	import { m } from '$paraglide/messages';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	export let form: SuperForm<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
</script>

<Accordion regionControl="font-bold">
	<AccordionItem open>
		<svelte:fragment slot="summary"
			><i class="fa-solid fa-bell mr-2"></i>{m.settingsNotifications()}</svelte:fragment
		>
		<svelte:fragment slot="content">
			<div class="p-4">
				<Checkbox
					{form}
					field="notifications_enable_mailing"
					label={m.settingsNotificationsMail()}
				/>
			</div>
		</svelte:fragment>
	</AccordionItem>
	<AccordionItem open>
		<svelte:fragment slot="summary">
			<i class="fa-solid fa-asterisk mr-2" />{m.settingsInterface()}
		</svelte:fragment>
		<svelte:fragment slot="content">
			<div class="p-4">
				<Checkbox
					{form}
					field="interface_agg_scenario_matrix"
					label={m.settingsAggregateMatrix()}
				/>
			</div>
		</svelte:fragment>
	</AccordionItem>
	<AccordionItem>
		<svelte:fragment slot="summary"
			><i class="fa-solid fa-gem mr-2"></i>{m.assets()}</svelte:fragment
		>
		<svelte:fragment slot="content">
			<Select
				{form}
				field="security_objective_scale"
				cacheLock={cacheLocks['security_objective_scale']}
				bind:cachedValue={formDataCache['security_objective_scale']}
				options={model.selectOptions['security_objective_scale']}
				helpText={m.securityObjectiveScaleHelpText()}
				label={m.securityObjectiveScale()}
			/>
		</svelte:fragment>
	</AccordionItem>
	<AccordionItem>
		<svelte:fragment slot="summary"
			><i class="fa-solid fa-gopuram mr-2"></i>{m.ebiosRadarParameters()}</svelte:fragment
		>
		<svelte:fragment slot="content">
			<NumberField
				{form}
				field="ebios_radar_max"
				label={m.maxRadius()}
				min={6}
				max={16}
				step={0.1}
				cacheLock={cacheLocks['ebios_radar_max']}
				bind:cachedValue={formDataCache['ebios_radar_max']}
			/>
			<NumberField
				{form}
				field="ebios_radar_green_zone_radius"
				label={m.greenZoneRadius()}
				min={0.1}
				max={16}
				step={0.1}
				cacheLock={cacheLocks['ebios_radar_green_zone_radius']}
				bind:cachedValue={formDataCache['ebios_radar_green_zone_radius']}
			/>
			<NumberField
				{form}
				field="ebios_radar_yellow_zone_radius"
				label={m.yellowZoneRadius()}
				min={0.5}
				max={16}
				step={0.1}
				cacheLock={cacheLocks['ebios_radar_yellow_zone_radius']}
				bind:cachedValue={formDataCache['ebios_radar_yellow_zone_radius']}
			/>
			<NumberField
				{form}
				field="ebios_radar_red_zone_radius"
				label={m.redZoneRadius()}
				min={1}
				max={16}
				step={0.1}
				cacheLock={cacheLocks['ebios_radar_red_zone_radius']}
				bind:cachedValue={formDataCache['ebios_radar_red_zone_radius']}
			/>
		</svelte:fragment>
	</AccordionItem>
</Accordion>
