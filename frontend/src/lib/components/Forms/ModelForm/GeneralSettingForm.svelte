<script lang="ts">
	import Select from '../Select.svelte';
	import NumberField from '../NumberField.svelte';
	import { m } from '$paraglide/messages';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';
	import { Accordion } from '@skeletonlabs/skeleton-svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import RadioGroup from '../RadioGroup.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
	}

	let { form, model, cacheLocks = {} }: Props = $props();
	let formDataCache = $state({});

	const formStore = form.form;
	const modalStore = getModalStore();

	let flipVertically = $derived(formDataCache['risk_matrix_flip_vertical'] ?? false);

	let xAxis = $derived(formDataCache['risk_matrix_swap_axes'] ? 'probability' : 'impact');
	let yAxis = $derived(formDataCache['risk_matrix_swap_axes'] ? 'impact' : 'probability');
	let xAxisLabel = $derived(safeTranslate(`${xAxis}${$formStore.risk_matrix_labels ?? 'ISO'}`));
	let yAxisLabel = $derived(safeTranslate(`${yAxis}${$formStore.risk_matrix_labels ?? 'ISO'}`));

	let horizontalAxisPos = $derived(flipVertically ? 'top-8' : 'bottom-8');
	let horizontalLabelPos = $derived(flipVertically ? 'top-2' : 'bottom-2');

	let openAccordionItems = $state(['notifications', 'financial']);

	// Track original currency for change detection
	let originalCurrency = $state($formStore.currency);
	let conversionRateValue = $state('1.0');

	function handleCurrencyChange(newCurrency: string) {
		if (originalCurrency && originalCurrency !== newCurrency) {
			// Show modal to ask for conversion rate
			const modal: ModalSettings = {
				type: 'prompt',
				title: m.currencyConversionRate?.() || 'Currency Conversion Rate',
				body: `Converting from ${originalCurrency} to ${newCurrency}. Enter conversion rate (default: 1.0):`,
				value: '1.0',
				valueAttr: {
					type: 'text',
					pattern: '[0-9]+([\\.][0-9]+)?',
					required: true,
					placeholder: '1.0'
				},
				response: (rate: string | false) => {
					if (rate !== false && rate !== null && rate !== '') {
						// Validate it's a valid number
						const n = Number(rate);
						if (Number.isFinite(n) && n > 0) {
							conversionRateValue = rate.toString();
							// Accept change
							originalCurrency = newCurrency;
						} else {
							// Revert currency change
							$formStore.currency = originalCurrency;
							conversionRateValue = '1.0';
						}
					} else {
						// User cancelled - revert currency
						$formStore.currency = originalCurrency;
						conversionRateValue = '1.0';
					}
				}
			};
			modalStore.trigger(modal);
		} else {
			// No currency change, reset conversion rate
			conversionRateValue = '1.0';
		}
	}
</script>

<!-- Hidden input to send conversion_rate with the form -->
<input type="hidden" name="conversion_rate" value={conversionRateValue} />

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
	<Accordion.Item value="assets">
		{#snippet control()}
			<i class="fa-solid fa-gem mr-2"></i>{m.assets()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4">
				<Select
					{form}
					field="security_objective_scale"
					cacheLock={cacheLocks['security_objective_scale']}
					bind:cachedValue={formDataCache['security_objective_scale']}
					options={model.selectOptions['security_objective_scale']}
					helpText={m.securityObjectiveScaleHelpText()}
					label={m.securityObjectiveScale()}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="riskMatrix">
		{#snippet control()}
			<i class="fa-solid fa-table-cells-large mr-2"></i>{m.settingsRiskMatrix()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4 flex flex-row gap-4">
				<div class="flex flex-col flex-1 space-y-4">
					<Checkbox
						{form}
						field="interface_agg_scenario_matrix"
						label={m.settingsAggregateMatrix()}
					/>
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
					<RadioGroup
						possibleOptions={[
							{ label: m.iso27005(), value: 'ISO' },
							{ label: m.ebiosRM(), value: 'EBIOS' }
						]}
						{form}
						key="value"
						labelKey="label"
						field="risk_matrix_labels"
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
			<div class="p-4 space-y-4">
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
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="financial">
		{#snippet control()}
			<i class="fa-solid fa-coins mr-2"></i>{m.financialSettings()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4 space-y-4">
				<Select
					{form}
					field="currency"
					options={[
						{ label: 'Euro (€)', value: '€' },
						{ label: 'US Dollar ($)', value: '$' },
						{ label: 'British Pound (£)', value: '£' },
						{ label: 'Japanese Yen (¥)', value: '¥' },
						{ label: 'Canadian Dollar (C$)', value: 'C$' },
						{ label: 'Australian Dollar (A$)', value: 'A$' },
						{ label: 'New Zealand Dollar (NZ$)', value: 'NZ$' },
						{ label: 'Swiss Franc (CHF)', value: 'CHF' }
					]}
					label={m.currency()}
					helpText={m.currencyHelpText()}
					onchange={(e) => handleCurrencyChange(e.target.value)}
				/>
				<NumberField
					{form}
					field="daily_rate"
					label={m.dailyRate()}
					helpText={m.dailyRateHelpText()}
					min={0}
					step={1}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="mappings">
		{#snippet control()}
			<i class="fa-solid fa-diagram-project mr-2"></i>{m.requirementMappingSets()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4">
				<NumberField
					{form}
					field="mapping_max_depth"
					label={m.mappingMaxDepth()}
					helpText={m.mappingMaxDepthHelpText()}
					min={2}
					max={5}
					step={1}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="workflows">
		{#snippet control()}
			<i class="fa-solid fa-code-branch mr-2"></i>{m.workflows()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4">
				<Checkbox
					{form}
					field="allow_self_validation"
					label={m.allowSelfValidation()}
					helpText={m.allowSelfValidationHelpText()}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="security">
		{#snippet control()}
			<i class="fa-solid fa-shield-halved mr-2"></i>{m.security()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4">
				<Checkbox
					{form}
					field="show_warning_external_links"
					label={m.showWarningExternalLinks()}
					helpText={m.showWarningExternalLinksHelpText()}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
	<Accordion.Item value="assignments">
		{#snippet control()}
			<i class="fa-solid fa-clipboard-user mr-2"></i>{m.assignmentSettings()}
		{/snippet}
		{#snippet panel()}
			<div class="p-4">
				<Checkbox
					{form}
					field="allow_assignments_to_entities"
					label={m.allowAssignmentsToEntities()}
					helpText={m.allowAssignmentsToEntitiesDescription()}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
</Accordion>
