<script lang="ts">
	import Select from '../Select.svelte';
	import NumberField from '../NumberField.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import { m } from '$paraglide/messages';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperForm } from 'sveltekit-superforms';
	import { Accordion } from '@skeletonlabs/skeleton-svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import RadioGroup from '../RadioGroup.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { LOCALE_MAP, language, defaultLangLabels } from '$lib/utils/locales';
	import { setLocale } from '$paraglide/runtime';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';

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
	const toastStore = getToastStore();

	let ollamaModels = $state<{ label: string; value: string }[]>([]);
	let ollamaModelsLoading = $state(false);

	async function fetchOllamaModels() {
		ollamaModelsLoading = true;
		try {
			const res = await fetch('/fe-api/chat/ollama-models');
			if (res.ok) {
				const data = await res.json();
				ollamaModels = (data.models || []).map((m: { name: string }) => ({
					label: m.name,
					value: m.name
				}));
			}
		} catch {
			// Ollama not reachable — leave empty, text field fallback
		}
		ollamaModelsLoading = false;
	}

	let flipVertically = $derived(formDataCache['risk_matrix_flip_vertical'] ?? false);

	let xAxis = $derived(formDataCache['risk_matrix_swap_axes'] ? 'probability' : 'impact');
	let yAxis = $derived(formDataCache['risk_matrix_swap_axes'] ? 'impact' : 'probability');
	let xAxisLabel = $derived(safeTranslate(`${xAxis}${$formStore.risk_matrix_labels ?? 'ISO'}`));
	let yAxisLabel = $derived(safeTranslate(`${yAxis}${$formStore.risk_matrix_labels ?? 'ISO'}`));

	let horizontalAxisPos = $derived(flipVertically ? 'top-8' : 'bottom-8');
	let horizontalLabelPos = $derived(flipVertically ? 'top-2' : 'bottom-2');

	let openAccordionItems = $state([]);

	// Track original currency for change detection
	let originalCurrency = $state($formStore.currency);
	let conversionRateValue = $state('1.0');

	let forceLanguageInProgress = $state(false);

	function handleForceLanguage() {
		const firstModal: ModalSettings = {
			type: 'confirm',
			title: m.forceLanguageConfirmTitle(),
			body: m.forceLanguageConfirmBody(),
			response: (confirmed: boolean) => {
				if (!confirmed) return;
				const secondModal: ModalSettings = {
					type: 'confirm',
					title: m.forceLanguageFinalConfirmTitle(),
					body: m.forceLanguageFinalConfirmBody(),
					response: async (confirmed2: boolean) => {
						if (!confirmed2) return;
						forceLanguageInProgress = true;
						try {
							const res = await fetch('/settings/force-language', {
								method: 'POST',
								headers: { 'Content-Type': 'application/json' }
							});
							const data = await res.json();
							if (res.ok) {
								toastStore.trigger({
									message: m.forceLanguageSuccess(),
									preset: 'success'
								});
								if (data.language) {
									setLocale(data.language);
								}
							} else {
								toastStore.trigger({
									message: data.error || m.forceLanguageFailed(),
									preset: 'error'
								});
							}
						} finally {
							forceLanguageInProgress = false;
						}
					}
				};
				modalStore.trigger(secondModal);
			}
		};
		modalStore.trigger(firstModal);
	}

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
	<Accordion.Item value="language">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-language mr-2"></i><span class="flex-1 text-left"
				>{m.languageSettings()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
			<div class="p-4 space-y-4">
				<Select
					{form}
					field="default_language"
					options={(model.selectOptions?.['default_language'] ?? []).map(
						(opt: { label: string; value: string }) => ({
							value: opt.value,
							label: `${defaultLangLabels[opt.value] ?? opt.value} (${language[LOCALE_MAP[opt.value]?.name] ?? opt.label})`
						})
					)}
					label={m.defaultLanguage()}
					helpText={m.defaultLanguageHelpText()}
				/>
				<hr class="my-2" />
				<p class="text-sm text-gray-500">{m.forceLanguageHelpText()}</p>
				<button
					type="button"
					class="btn preset-filled-warning-500 text-sm"
					onclick={handleForceLanguage}
					disabled={forceLanguageInProgress}
				>
					<i class="fa-solid fa-users mr-2"></i>
					{m.forceLanguageForAllUsers()}
				</button>
			</div>
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="notifications">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-bell mr-2"></i><span class="flex-1 text-left"
				>{m.settingsNotifications()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
			<div class="p-4">
				<Checkbox
					{form}
					field="notifications_enable_mailing"
					label={m.settingsNotificationsMail()}
				/>
			</div>
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="assets">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-gem mr-2"></i><span class="flex-1 text-left">{m.assets()}</span>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
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
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="riskMatrix">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-table-cells-large mr-2"></i><span class="flex-1 text-left"
				>{m.settingsRiskMatrix()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
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
						<!-- Point d'origine -->
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
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="ebiosRadar">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-gopuram mr-2"></i><span class="flex-1 text-left"
				>{m.ebiosRadarParameters()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
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
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="financial">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-coins mr-2"></i><span class="flex-1 text-left"
				>{m.financialSettings()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
			<div class="p-4 space-y-4">
				<Select
					{form}
					field="currency"
					options={[
						{ label: 'Euro (€)', value: '€' },
						{ label: 'US Dollar ($)', value: '$' },
						{ label: 'British Pound (£)', value: '£' },
						{ label: 'Japanese Yen (¥)', value: '¥' },
						{ label: 'Chinese Yuan (CN¥)', value: 'CN¥' },
						{ label: 'Indian Rupee (₹)', value: '₹' },
						{ label: 'South Korean Won (₩)', value: '₩' },
						{ label: 'Canadian Dollar (C$)', value: 'C$' },
						{ label: 'Australian Dollar (A$)', value: 'A$' },
						{ label: 'New Zealand Dollar (NZ$)', value: 'NZ$' },
						{ label: 'Swiss Franc (CHF)', value: 'CHF' },
						{ label: 'Singapore Dollar (S$)', value: 'S$' },
						{ label: 'Hong Kong Dollar (HK$)', value: 'HK$' },
						{ label: 'Swedish Krona (SEK)', value: 'SEK' },
						{ label: 'Norwegian Krone (NOK)', value: 'NOK' },
						{ label: 'Danish Krone (DKK)', value: 'DKK' },
						{ label: 'Brazilian Real (R$)', value: 'R$' },
						{ label: 'Mexican Peso (MX$)', value: 'MX$' },
						{ label: 'South African Rand (ZAR)', value: 'ZAR' },
						{ label: 'Turkish Lira (₺)', value: '₺' },
						{ label: 'Polish Złoty (PLN)', value: 'PLN' },
						{ label: 'Taiwan Dollar (NT$)', value: 'NT$' },
						{ label: 'Thai Baht (฿)', value: '฿' },
						{ label: 'Malaysian Ringgit (MYR)', value: 'MYR' }
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
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="mappings">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-diagram-project mr-2"></i><span class="flex-1 text-left"
				>{m.requirementMappingSets()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
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
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="workflows">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-code-branch mr-2"></i><span class="flex-1 text-left"
				>{m.workflows()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
			<div class="p-4">
				<Checkbox
					{form}
					field="allow_self_validation"
					label={m.allowSelfValidation()}
					helpText={m.allowSelfValidationHelpText()}
				/>
			</div>
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="security">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-shield-halved mr-2"></i><span class="flex-1 text-left"
				>{m.security()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
			<div class="p-4 space-y-4">
				<Checkbox
					{form}
					field="show_warning_external_links"
					label={m.showWarningExternalLinks()}
					helpText={m.showWarningExternalLinksHelpText()}
				/>
				<Checkbox
					{form}
					field="enforce_mfa"
					label={m.enforceMfa()}
					helpText={m.enforceMfaHelpText()}
				/>
			</div>
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="chatAi">
		<Accordion.ItemTrigger
			class="flex w-full items-center cursor-pointer"
			onclick={fetchOllamaModels}
		>
			<i class="fa-solid fa-robot mr-2"></i><span class="flex-1 text-left"
				>{m.chatAiSettings()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
			<div class="p-4 space-y-4">
				<TextField
					{form}
					field="ollama_base_url"
					label={m.ollamaBaseUrl()}
					helpText={m.ollamaBaseUrlHelpText()}
				/>
				{#if ollamaModels.length > 0}
					<Select
						{form}
						field="ollama_model"
						options={ollamaModels}
						label={m.ollamaModel()}
						helpText={m.ollamaModelHelpText()}
						translateOptions={false}
					/>
					<Select
						{form}
						field="ollama_embed_model"
						options={ollamaModels}
						label={m.ollamaEmbedModel()}
						helpText={m.ollamaEmbedModelHelpText()}
						translateOptions={false}
					/>
				{:else}
					<TextField
						{form}
						field="ollama_model"
						label={m.ollamaModel()}
						helpText={ollamaModelsLoading
							? 'Loading models from Ollama...'
							: m.ollamaModelHelpText()}
					/>
					<TextField
						{form}
						field="ollama_embed_model"
						label={m.ollamaEmbedModel()}
						helpText={ollamaModelsLoading
							? 'Loading models from Ollama...'
							: m.ollamaEmbedModelHelpText()}
					/>
				{/if}
				<Select
					{form}
					field="embedding_backend"
					options={[
						{ label: 'Sentence Transformers (local)', value: 'sentence-transformers' },
						{ label: 'Ollama', value: 'ollama' }
					]}
					label={m.embeddingBackend()}
					helpText={m.embeddingBackendHelpText()}
				/>
				<TextArea
					{form}
					field="chat_system_prompt"
					label={m.chatSystemPrompt()}
					helpText={m.chatSystemPromptHelpText()}
				/>
			</div>
		</Accordion.ItemContent>
	</Accordion.Item>
	<Accordion.Item value="assignments">
		<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
			<i class="fa-solid fa-clipboard-user mr-2"></i><span class="flex-1 text-left"
				>{m.assignmentSettings()}</span
			>
			<Accordion.ItemIndicator
				class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
				><svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512"
					><path
						d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
					/></svg
				></Accordion.ItemIndicator
			>
		</Accordion.ItemTrigger>
		<Accordion.ItemContent>
			<div class="p-4">
				<Checkbox
					{form}
					field="allow_assignments_to_entities"
					label={m.allowAssignmentsToEntities()}
					helpText={m.allowAssignmentsToEntitiesDescription()}
				/>
			</div>
		</Accordion.ItemContent>
	</Accordion.Item>
</Accordion>
