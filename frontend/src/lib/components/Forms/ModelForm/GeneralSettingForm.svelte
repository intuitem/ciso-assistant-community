<script lang="ts">
	import Select from '../Select.svelte';
	import NumberField from '../NumberField.svelte';
	import { m } from '$paraglide/messages';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';
	import { Accordion } from '@skeletonlabs/skeleton-svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import RadioGroupInput from '../RadioGroupInput.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
	}

	let { form, model, cacheLocks = {} }: Props = $props();
	let formDataCache = $state({});

	const formStore = form.form;

	$effect(() => console.log('formDataCache', formDataCache));

	let flipVertically = $derived(formDataCache['risk_matrix_flip_vertical'] ?? false);
	let xAxis = $derived(formDataCache['risk_matrix_swap_axes'] ? 'probability' : 'impact');
	let yAxis = $derived(formDataCache['risk_matrix_swap_axes'] ? 'impact' : 'probability');
	let xAxisLabel = $derived(safeTranslate(`${xAxis}${$formStore.risk_matrix_labels ?? 'ISO'}`));
	let yAxisLabel = $derived(safeTranslate(`${yAxis}${$formStore.risk_matrix_labels ?? 'ISO'}`));

	let horizontalAxisPos = $derived(flipVertically ? 'top-8' : 'bottom-8');
	let horizontalLabelPos = $derived(flipVertically ? 'top-2' : 'bottom-2');

	let openAccordionItems = $state(['notifications', 'interface']);
</script>

<Accordion
	value={openAccordionItems}
	onValueChange={(e) => (openAccordionItems = e.value)}
	multiple
>
	<Accordion.Item value="notifications">
		{#snippet control()}
			<i class="fa-solid fa-bell mr-2"></i>{m.settingsNotifications()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4">
				<Checkbox
					{form}
					field="notifications_enable_mailing"
					label={m.settingsNotificationsMail()}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="interface">
		{#snippet control()}
			<i class="fa-solid fa-asterisk mr-2"></i>{m.settingsInterface()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4">
				<Checkbox
					{form}
					field="interface_agg_scenario_matrix"
					label={m.settingsAggregateMatrix()}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="assets">
		{#snippet control()}
			<i class="fa-solid fa-gem mr-2"></i>{m.assets()}
		{/snippet}
		{#snippet panel()}
			<Select
				{form}
				field="security_objective_scale"
				cacheLock={cacheLocks['security_objective_scale']}
				bind:cachedValue={formDataCache['security_objective_scale']}
				options={model.selectOptions['security_objective_scale']}
				helpText={m.securityObjectiveScaleHelpText()}
				label={m.securityObjectiveScale()}
			/>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="riskMatrix">
		{#snippet control()}
			<i class="fa-solid fa-table-cells-large mr-2"></i>{m.settingsRiskMatrix()}
		{/snippet}
		{#snippet panel()}
			<div class="flex flex-row gap-4">
				<div class="flex flex-col flex-1 space-y-4">
					<Checkbox
						{form}
						field="risk_matrix_swap_axes"
						label={m.settingsRiskMatrixSwapAxes()}
						helpText={m.settingsRiskMatrixSwapAxesHelpText()}
						bind:cachedValue={formDataCache['risk_matrix_swap_axes']}
					/>
					<Checkbox
						{form}
						field="risk_matrix_flip_vertical"
						label={m.settingsRiskMatrixFlipVertical()}
						helpText={m.settingsRiskMatrixFlipVerticalHelpText()}
						bind:cachedValue={formDataCache['risk_matrix_flip_vertical']}
					/>
					<RadioGroupInput
						{form}
						label={m.settingsRiskMatrixLabels()}
						field="risk_matrix_labels"
						options={[
							{ label: m.iso27005(), value: 'ISO' },
							{ label: m.ebiosRM(), value: 'EBIOS' }
						]}
					/>
				</div>
				<div class="flex-1">
					<div class="relative w-full h-64 max-w-md bg-white rounded-lg shadow-md p-4">
						<!-- Point d’origine -->
						<div class={`absolute ${horizontalAxisPos} left-8 w-2 h-2 bg-black rounded-full`}></div>

						<!-- Axe horizontal -->
						<div class={`absolute ${horizontalAxisPos} left-8 w-4/5 h-0.5 bg-black`}></div>

						<!-- Label axe horizontal -->
						<div
							class={`absolute ${horizontalLabelPos} left-1/2 transform -translate-x-1/2 text-center`}
						>
							<span class="font-medium">{xAxisLabel}</span>
						</div>

						<!-- Axe vertical -->
						<div class={`absolute ${horizontalAxisPos} left-8 w-0.5 h-4/5 bg-black`}></div>

						<!-- Label axe vertical -->
						<div class="absolute top-1/2 left-4 transform -translate-y-1/2 -rotate-90 origin-left">
							<span class="font-medium">{yAxisLabel}</span>
						</div>
					</div>
				</div>
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="ebiosRadar">
		{#snippet control()}
			<i class="fa-solid fa-gopuram mr-2"></i>{m.ebiosRadarParameters()}
		{/snippet}
		{#snippet panel()}
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
		{/snippet}
	</Accordion.Item>
</Accordion>
