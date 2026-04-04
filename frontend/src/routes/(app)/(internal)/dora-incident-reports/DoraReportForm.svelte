<script lang="ts">
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { modelSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages.js';
	import { safeTranslate } from '$lib/utils/i18n';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import type { SuperValidated } from 'sveltekit-superforms';

	interface Props {
		form: SuperValidated<any>;
		selectOptions: Record<string, any[]>;
		allChoices: Record<string, { label: string; value: string }[]>;
		mode: 'create' | 'edit';
		formAction: string;
		incidentRef?: { id: string; name: string } | null;
		reportId?: string | null;
		validation?: { valid: boolean; errors: string[] } | null;
		userOptions?: { id: string; label: string; email: string }[];
	}

	let {
		form,
		selectOptions,
		allChoices,
		mode,
		formAction,
		incidentRef = null,
		reportId = null,
		validation = null,
		userOptions = []
	}: Props = $props();

	const schema = modelSchema('dora-incident-reports');

	const isSubmitted = form.data?.is_submitted === true;
	let showValidationErrors = $state(false);

	const canProgress =
		mode === 'edit' &&
		validation?.valid &&
		form.data?.incident_submission !== 'major_incident_reclassified_as_non-major';

	const _form = superForm(form, {
		dataType: 'json',
		invalidateAll: true,
		applyAction: true,
		resetForm: false,
		validators: zod(schema),
		taintedMessage: m.taintedFormMessage(),
		validationMethod: 'auto',
		onUpdated: async ({ form: updatedForm }) => {
			// In create mode: redirect to the new report's all-in-one page
			// In edit mode: stay on page (no redirect)
			if (mode === 'create' && updatedForm.message?.redirect) {
				goto(getSecureRedirect(updatedForm.message.redirect));
			}
		}
	});

	const formData = _form.form;

	// -- JSONField state management --
	// Initialize JSONField state from form data (use JSON round-trip to avoid proxy issues)
	function initCopy(val: any): any {
		return JSON.parse(JSON.stringify(val));
	}

	// Deep merge defaults with existing data (ensures nested keys always exist)
	function initImpactAssessment(data: any): Record<string, any> {
		const defaults = {
			serviceImpact: {},
			affectedAssets: {
				affectedClients: {},
				affectedFinancialCounterparts: {},
				affectedTransactions: {}
			}
		};
		const existing = initCopy(data || {});
		return {
			...defaults,
			...existing,
			serviceImpact: { ...defaults.serviceImpact, ...(existing.serviceImpact || {}) },
			affectedAssets: {
				...defaults.affectedAssets,
				...(existing.affectedAssets || {}),
				affectedClients: {
					...defaults.affectedAssets.affectedClients,
					...(existing.affectedAssets?.affectedClients || {})
				},
				affectedFinancialCounterparts: {
					...defaults.affectedAssets.affectedFinancialCounterparts,
					...(existing.affectedAssets?.affectedFinancialCounterparts || {})
				},
				affectedTransactions: {
					...defaults.affectedAssets.affectedTransactions,
					...(existing.affectedAssets?.affectedTransactions || {})
				}
			}
		};
	}

	let incidentType: Record<string, any> = $state(initCopy($formData.incident_type || {}));
	let classificationTypes: Record<string, any>[] = $state(
		initCopy($formData.classification_types || [])
	);
	let impactAssessment: Record<string, any> = $state(
		initImpactAssessment($formData.impact_assessment)
	);
	let serviceImpact = $derived(impactAssessment.serviceImpact);
	let affectedAssets = $derived(impactAssessment.affectedAssets);
	let rootCauseHl: string[] = $state(initCopy($formData.root_cause_hl_classification || []));
	let rootCauseDetailed: string[] = $state(
		initCopy($formData.root_causes_detailed_classification || [])
	);
	let rootCauseAdditional: string[] = $state(
		initCopy($formData.root_causes_additional_classification || [])
	);
	let reportingAuthorities: string[] = $state(
		initCopy($formData.reporting_to_other_authorities || [])
	);

	// Sync state back to form fields using JSON round-trip (structuredClone fails on proxy objects)
	function deepCopy(obj: any): any {
		return JSON.parse(JSON.stringify(obj));
	}

	$effect(() => {
		$formData.incident_type = deepCopy(incidentType);
	});
	$effect(() => {
		$formData.classification_types = deepCopy(classificationTypes);
	});
	$effect(() => {
		$formData.impact_assessment = deepCopy(impactAssessment);
	});
	$effect(() => {
		$formData.root_cause_hl_classification = [...rootCauseHl];
	});
	$effect(() => {
		$formData.root_causes_detailed_classification = [...rootCauseDetailed];
	});
	$effect(() => {
		$formData.root_causes_additional_classification = [...rootCauseAdditional];
	});
	$effect(() => {
		$formData.reporting_to_other_authorities = [...reportingAuthorities];
	});

	// -- Helpers --
	function toggleArrayValue(arr: string[], value: string): string[] {
		return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
	}

	function addClassificationCriterion() {
		classificationTypes = [...classificationTypes, { classificationCriterion: '' }];
	}

	function removeClassificationCriterion(index: number) {
		classificationTypes = classificationTypes.filter((_, i) => i !== index);
	}

	function cancel() {
		if (browser) {
			const url = new URL(window.location.href);
			const next = getSecureRedirect(url.searchParams.get('next'));
			if (next) window.location.href = next;
			else history.back();
		}
	}

	// Derived state for conditional fields
	let isCyberIncident = $derived(
		(incidentType.incidentClassification || []).includes('cybersecurity-related')
	);
	let hasOtherClassification = $derived(
		(incidentType.incidentClassification || []).includes('other')
	);
	let hasOtherTechnique = $derived((incidentType.threatTechniques || []).includes('other'));
	let hasOtherAuthority = $derived(reportingAuthorities.includes('other'));

	// Clear dependent values when controlling option is turned off
	$effect(() => {
		if (!isCyberIncident) {
			delete incidentType.threatTechniques;
			delete incidentType.otherThreatTechniques;
			delete incidentType.indicatorsOfCompromise;
		}
	});
	$effect(() => {
		if (!hasOtherClassification) {
			delete incidentType.otherIncidentClassification;
		}
	});
	$effect(() => {
		if (!hasOtherTechnique) {
			delete incidentType.otherThreatTechniques;
		}
	});
	$effect(() => {
		if (!hasOtherAuthority) {
			$formData.reporting_to_other_authorities_other = '';
		}
	});
	$effect(() => {
		if (impactAssessment.isAffectedInfrastructureComponents !== 'yes') {
			delete impactAssessment.affectedInfrastructureComponents;
		}
	});

	// Map validation error paths to form section IDs
	// Errors look like: "incident: 'incidentDescription' is a required property"
	// or: "incident.financialEntityCode: '' is too short"
	// or: "(root): 'classificationTypes' is a required property"
	function getErrorSection(error: string): string | null {
		const e = error.toLowerCase();

		// Section 1: Metadata
		if (e.includes('incidentsubmission') || e.includes('reportcurrency')) return 'dora-section-1';

		// Section 2: Entities & Contacts
		if (
			e.includes('submittingentity') ||
			e.includes('affectedentity') ||
			e.includes('ultimateparent') ||
			e.includes('contact')
		)
			return 'dora-section-2';

		// Section 4: Incident Type (check before general incident)
		if (
			e.includes('incidenttype') ||
			e.includes('incidentclassification') ||
			e.includes('threattechniques') ||
			e.includes('indicatorsofcompromise')
		)
			return 'dora-section-4';

		// Section 5: Classification Criteria
		if (e.includes('classificationtypes') || e.includes('classificationcriterion'))
			return 'dora-section-5';

		// Section 6: Root Cause
		if (e.includes('rootcause')) return 'dora-section-6';

		// Section 7: Impact Assessment
		if (
			e.includes('impactassessment') ||
			e.includes('serviceimpact') ||
			e.includes('affectedassets') ||
			e.includes('affectedclients') ||
			e.includes('affectedfinancial') ||
			e.includes('affectedtransaction') ||
			e.includes('infrastructure')
		)
			return 'dora-section-7';

		// Section 8: Resolution & Financial
		if (
			e.includes('resolution') ||
			e.includes('financialrecoveries') ||
			e.includes('grossamount') ||
			e.includes('criticalfunctions')
		)
			return 'dora-section-8';

		// Section 9: Reporting & Recurring
		if (e.includes('reportingtoother') || e.includes('recurring') || e.includes('downtimeactual'))
			return 'dora-section-9';

		// Section 3: Incident Details (catch-all for incident.*)
		if (e.includes('incident')) return 'dora-section-3';

		return null;
	}

	function scrollToError(error: string) {
		const sectionId = getErrorSection(error);
		if (sectionId) {
			const el = document.getElementById(sectionId);
			if (el) {
				el.scrollIntoView({ behavior: 'smooth', block: 'start' });
				// Brief highlight
				el.classList.add('ring-2', 'ring-amber-400', 'ring-offset-2');
				setTimeout(() => el.classList.remove('ring-2', 'ring-amber-400', 'ring-offset-2'), 2000);
			}
		}
	}

	// Group detailed root causes by category prefix (e.g., "Malicious actions — X" → group "Malicious actions")
	const detailedGroups = (() => {
		const groups = new Map<string, { value: string; label: string; shortLabel: string }[]>();
		for (const choice of allChoices.rootCauseDetailed) {
			const parts = choice.label.split(' — ');
			const group = parts.length > 1 ? parts[0] : 'Other';
			const label = parts.length > 1 ? parts[1] : choice.label;
			if (!groups.has(group)) groups.set(group, []);
			groups.get(group)!.push({ ...choice, shortLabel: label });
		}
		return [...groups.entries()];
	})();

	const modalStore: ModalStore = getModalStore();

	function modalMarkSubmitted(): void {
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal,
			props: {
				_form: { id: reportId },
				formAction: '?/markSubmitted',
				bodyComponent: undefined
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.markAsSubmitted(),
			body: m.submittedReport()
		};
		modalStore.trigger(modal);
	}

	// Fill contact fields from a selected user
	function fillContact(prefix: 'primary' | 'secondary', userId: string) {
		const user = userOptions.find((u) => u.id === userId);
		if (!user) return;
		$formData[`${prefix}_contact_name`] = user.label;
		$formData[`${prefix}_contact_email`] = user.email;
	}
</script>

<div class="max-w-5xl mx-auto p-4">
	<!-- Header bar -->
	<div class="flex items-center justify-between mb-6">
		<div>
			{#if incidentRef}
				<div class="flex items-center gap-2 text-sm mb-1">
					<Anchor
						class="text-gray-500 hover:text-primary-500 transition-colors"
						href="/incidents/{incidentRef.id}"
						prefixCrumbs={[{ label: safeTranslate('incidents'), href: '/incidents' }]}
					>
						<i class="fa-solid fa-arrow-left mr-1"></i>{incidentRef.name}
					</Anchor>
				</div>
			{/if}
			<h1 class="text-2xl font-bold text-gray-900">
				{mode === 'create' ? safeTranslate('add-doraIncidentReport') : m.doraIncidentReport()}
			</h1>
		</div>
		{#if validation && mode === 'edit'}
			<div class="flex-shrink-0">
				{#if validation.valid}
					<span
						class="inline-flex items-center gap-2 bg-green-50 text-green-700 border border-green-200 px-4 py-2 rounded-full text-sm font-medium"
					>
						<i class="fa-solid fa-check-circle"></i>{m.schemaValid()}
					</span>
				{:else}
					<button
						class="inline-flex items-center gap-2 bg-amber-50 text-amber-700 border border-amber-200 px-4 py-2 rounded-full text-sm font-medium hover:bg-amber-100 transition-colors"
						onclick={() => (showValidationErrors = !showValidationErrors)}
					>
						<i class="fa-solid fa-triangle-exclamation"></i>{m.schemaInvalid()}
						<span class="bg-amber-200 text-amber-800 rounded-full px-2 py-0.5 text-xs"
							>{validation.errors?.length || 0}</span
						>
						<i class="fa-solid fa-chevron-{showValidationErrors ? 'up' : 'down'} text-xs ml-1"></i>
					</button>
				{/if}
			</div>
		{/if}
	</div>

	{#if showValidationErrors && validation && !validation.valid}
		<div class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-2 space-y-2">
			<div class="flex items-center justify-between">
				<span class="text-sm font-semibold text-amber-800">{m.schemaInvalid()}</span>
				<button
					class="text-amber-600 hover:text-amber-800 text-xs"
					onclick={() => (showValidationErrors = false)}
				>
					<i class="fa-solid fa-xmark"></i>
				</button>
			</div>
			<ul class="space-y-1">
				{#each validation.errors as error}
					<li>
						<button
							type="button"
							class="w-full text-left flex items-start gap-2 px-2 py-1 rounded hover:bg-amber-100 transition-colors group"
							onclick={() => scrollToError(error)}
						>
							{#if getErrorSection(error)}
								<i
									class="fa-solid fa-arrow-right text-[10px] mt-1.5 flex-shrink-0 text-amber-400 group-hover:text-amber-600 transition-colors"
								></i>
							{:else}
								<i class="fa-solid fa-circle text-[4px] mt-2 flex-shrink-0 text-amber-400"></i>
							{/if}
							<span class="font-mono text-xs text-amber-800">{error}</span>
						</button>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if isSubmitted}
		<div
			class="flex items-center gap-3 bg-blue-50 border border-blue-200 text-blue-800 px-5 py-3 rounded-lg mb-6"
		>
			<i class="fa-solid fa-lock text-lg"></i>
			<span class="font-medium">{m.submittedReport()}</span>
		</div>
	{/if}

	<SuperForm
		class="flex flex-col space-y-6"
		data={form}
		dataType="json"
		{_form}
		validators={zod(schema)}
		action={formAction}
	>
		{#snippet children({ form: formCtx })}
			<fieldset disabled={isSubmitted} class="flex flex-col space-y-6">
				<!-- Section 1: Report Metadata -->
				<div class="dora-section" id="dora-section-1">
					<h2 class="dora-section-header">
						<span class="dora-step">1</span>
						<i class="fa-solid fa-file-lines"></i>{m.doraReportMetadata()}
					</h2>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<AutocompleteSelect
							form={_form}
							optionsEndpoint="incidents"
							field="incident"
							label={m.incident()}
							hidden={!!$formData.incident}
						/>
						<AutocompleteSelect
							form={_form}
							optionsEndpoint="folders"
							optionsUrlParams="content_type=DO&content_type=GL"
							field="folder"
							label={m.domain()}
							hidden={!!$formData.folder}
						/>
						<Select
							form={_form}
							options={selectOptions.incident_submission}
							field="incident_submission"
							label={m.incidentSubmission()}
						/>
						<Select
							form={_form}
							options={selectOptions.report_currency}
							field="report_currency"
							label={m.reportCurrency()}
						/>
					</div>
				</div>

				<!-- Section 2: Entities & Contacts -->
				<div class="dora-section" id="dora-section-2">
					<h2 class="dora-section-header">
						<span class="dora-step">2</span>
						<i class="fa-solid fa-building"></i>{m.doraEntitiesAndContacts()}
					</h2>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<AutocompleteSelect
							form={_form}
							optionsEndpoint="entities"
							optionsExtraFields={[['folder', 'str']]}
							field="submitting_entity"
							label={m.submittingEntity()}
							nullable
						/>
						<AutocompleteSelect
							form={_form}
							optionsEndpoint="entities"
							optionsExtraFields={[['folder', 'str']]}
							field="ultimate_parent_entity"
							label={m.ultimateParentEntity()}
							nullable
						/>
					</div>
					<AutocompleteSelect
						form={_form}
						optionsEndpoint="entities"
						optionsExtraFields={[['folder', 'str']]}
						field="affected_entities"
						label={m.affectedEntities()}
						multiple
					/>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
						<div class="space-y-3">
							<div class="flex items-center justify-between">
								<h3 class="font-medium text-sm text-gray-600">{m.doraPrimaryContact()}</h3>
								<select
									class="select text-xs w-auto max-w-48"
									onchange={(e) => {
										fillContact('primary', e.currentTarget.value);
										e.currentTarget.value = '';
									}}
								>
									<option value="">{safeTranslate('fillFromUser')}</option>
									{#each userOptions as user}
										<option value={user.id}>{user.label}</option>
									{/each}
								</select>
							</div>
							<TextField form={_form} field="primary_contact_name" label={m.primaryContactName()} />
							<TextField
								form={_form}
								field="primary_contact_email"
								label={m.primaryContactEmail()}
								type="email"
							/>
							<TextField
								form={_form}
								field="primary_contact_phone"
								label={m.primaryContactPhone()}
							/>
						</div>
						<div class="space-y-3">
							<div class="flex items-center justify-between">
								<h3 class="font-medium text-sm text-gray-600">{m.doraSecondaryContact()}</h3>
								<select
									class="select text-xs w-auto max-w-48"
									onchange={(e) => {
										fillContact('secondary', e.currentTarget.value);
										e.currentTarget.value = '';
									}}
								>
									<option value="">{safeTranslate('fillFromUser')}</option>
									{#each userOptions as user}
										<option value={user.id}>{user.label}</option>
									{/each}
								</select>
							</div>
							<TextField
								form={_form}
								field="secondary_contact_name"
								label={m.secondaryContactName()}
							/>
							<TextField
								form={_form}
								field="secondary_contact_email"
								label={m.secondaryContactEmail()}
								type="email"
							/>
							<TextField
								form={_form}
								field="secondary_contact_phone"
								label={m.secondaryContactPhone()}
							/>
						</div>
					</div>
				</div>

				<!-- Section 3: Incident Details -->
				<div class="dora-section" id="dora-section-3">
					<h2 class="dora-section-header">
						<span class="dora-step">3</span>
						<i class="fa-solid fa-circle-info"></i>{m.doraIncidentDetails()}
					</h2>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<TextField form={_form} field="financial_entity_code" label={m.financialEntityCode()} />
						<TextField
							form={_form}
							field="competent_authority_code"
							label={m.competentAuthorityCode()}
						/>
						<TextField
							form={_form}
							field="detection_date_time"
							label={m.detectionDateTime()}
							type="datetime-local"
						/>
						<TextField
							form={_form}
							field="classification_date_time"
							label={m.classificationDateTime()}
							type="datetime-local"
						/>
						<Select
							form={_form}
							options={selectOptions.incident_discovery}
							field="incident_discovery"
							label={m.incidentDiscovery()}
						/>
						<TextField
							form={_form}
							field="incident_duration"
							label={m.incidentDuration()}
							placeholder="HHH:MM:SS"
						/>
					</div>
					<MarkdownField
						form={_form}
						field="incident_description"
						label={m.incidentDescription()}
					/>
					<TextField
						form={_form}
						field="originates_from_third_party_provider"
						label={m.originatesFromThirdPartyProvider()}
					/>
					<MarkdownField form={_form} field="other_information" label={m.otherInformation()} />
				</div>

				<!-- Section 4: Incident Type -->
				<div class="dora-section" id="dora-section-4">
					<h2 class="dora-section-header">
						<span class="dora-step">4</span>
						<i class="fa-solid fa-tag"></i>{m.doraIncidentType()}
					</h2>
					<fieldset class="space-y-2">
						<legend class="text-sm font-medium text-gray-700 mb-1"
							>{m.incidentType()} — {m.incidentSubmission()}</legend
						>
						<div class="flex flex-wrap gap-3">
							{#each allChoices.incidentClassification as choice}
								<label class="flex items-center space-x-2 text-sm">
									<input
										type="checkbox"
										checked={(incidentType.incidentClassification || []).includes(choice.value)}
										onchange={() => {
											incidentType.incidentClassification = toggleArrayValue(
												incidentType.incidentClassification || [],
												choice.value
											);
										}}
										class="rounded"
									/>
									<span>{choice.label}</span>
								</label>
							{/each}
						</div>
					</fieldset>

					{#if hasOtherClassification}
						<div>
							<label class="text-sm font-medium text-gray-700" for="otherIncidentClassification"
								>{m.otherInformation()}</label
							>
							<input
								id="otherIncidentClassification"
								type="text"
								bind:value={incidentType.otherIncidentClassification}
								class="input w-full mt-1"
							/>
						</div>
					{/if}

					{#if isCyberIncident}
						<fieldset class="space-y-2 mt-4">
							<legend class="text-sm font-medium text-gray-700 mb-1"
								>{safeTranslate('threatTechniques')}</legend
							>
							<div class="flex flex-wrap gap-3">
								{#each allChoices.threatTechniques as choice}
									<label class="flex items-center space-x-2 text-sm">
										<input
											type="checkbox"
											checked={(incidentType.threatTechniques || []).includes(choice.value)}
											onchange={() => {
												incidentType.threatTechniques = toggleArrayValue(
													incidentType.threatTechniques || [],
													choice.value
												);
											}}
											class="rounded"
										/>
										<span>{choice.label}</span>
									</label>
								{/each}
							</div>
						</fieldset>

						{#if hasOtherTechnique}
							<div>
								<label class="text-sm font-medium text-gray-700" for="otherThreatTechniques"
									>{m.otherInformation()}</label
								>
								<input
									id="otherThreatTechniques"
									type="text"
									bind:value={incidentType.otherThreatTechniques}
									class="input w-full mt-1"
								/>
							</div>
						{/if}

						<div>
							<label class="text-sm font-medium text-gray-700" for="ioc"
								>{safeTranslate('indicatorsOfCompromise')}</label
							>
							<textarea
								id="ioc"
								bind:value={incidentType.indicatorsOfCompromise}
								class="textarea w-full mt-1"
								rows="3"
							></textarea>
						</div>
					{/if}
				</div>

				<!-- Section 5: Classification Criteria -->
				<div class="dora-section" id="dora-section-5">
					<h2 class="dora-section-header">
						<span class="dora-step">5</span>
						<i class="fa-solid fa-list-check"></i>{m.doraClassificationCriteria()}
					</h2>
					{#each classificationTypes as criterion, index}
						<div class="border rounded-lg p-4 space-y-3 bg-gray-50">
							<div class="flex justify-between items-center">
								<select
									bind:value={criterion.classificationCriterion}
									class="select w-full max-w-md"
								>
									<option value="">--</option>
									{#each allChoices.classificationCriterion as choice}
										<option value={choice.value}>{choice.label}</option>
									{/each}
								</select>
								<button
									type="button"
									class="btn btn-sm preset-filled-error-500 ml-2"
									onclick={() => removeClassificationCriterion(index)}
								>
									<i class="fa-solid fa-trash mr-1"></i>{m.removeCriterion()}
								</button>
							</div>

							{#if criterion.classificationCriterion === 'geographical_spread'}
								<div>
									<label class="text-sm font-medium text-gray-700"
										>{safeTranslate('memberStatesImpactTypeDescription')}</label
									>
									<textarea
										bind:value={criterion.memberStatesImpactTypeDescription}
										class="textarea w-full mt-1"
										rows="2"
									></textarea>
								</div>
							{:else if criterion.classificationCriterion === 'data_losses'}
								<div>
									<label class="text-sm font-medium text-gray-700"
										>{safeTranslate('dataLossesDescription')}</label
									>
									<textarea
										bind:value={criterion.dataLossesDescription}
										class="textarea w-full mt-1"
										rows="2"
									></textarea>
								</div>
							{:else if criterion.classificationCriterion === 'reputational_impact'}
								<div>
									<label class="text-sm font-medium text-gray-700"
										>{safeTranslate('reputationalImpactDescription')}</label
									>
									<textarea
										bind:value={criterion.reputationalImpactDescription}
										class="textarea w-full mt-1"
										rows="2"
									></textarea>
								</div>
							{:else if criterion.classificationCriterion === 'economic_impact'}
								<div>
									<label class="text-sm font-medium text-gray-700"
										>{safeTranslate('economicImpactMaterialityThreshold')}</label
									>
									<input
										type="text"
										bind:value={criterion.economicImpactMaterialityThreshold}
										class="input w-full mt-1"
									/>
								</div>
							{/if}
						</div>
					{/each}
					<button
						type="button"
						class="btn preset-filled-secondary-500"
						onclick={addClassificationCriterion}
					>
						<i class="fa-solid fa-plus mr-2"></i>{m.addCriterion()}
					</button>
				</div>

				<!-- Section 6: Root Cause Analysis -->
				<div class="dora-section" id="dora-section-6">
					<h2 class="dora-section-header">
						<span class="dora-step">6</span>
						<i class="fa-solid fa-magnifying-glass"></i>{m.doraRootCauseAnalysis()}
					</h2>

					<fieldset class="space-y-2">
						<legend class="text-sm font-medium text-gray-700 mb-1"
							>{m.rootCauseHlClassification()}</legend
						>
						<div class="flex flex-wrap gap-3">
							{#each allChoices.rootCauseHl as choice}
								<label class="flex items-center space-x-2 text-sm">
									<input
										type="checkbox"
										checked={rootCauseHl.includes(choice.value)}
										onchange={() => (rootCauseHl = toggleArrayValue(rootCauseHl, choice.value))}
										class="rounded"
									/>
									<span>{choice.label}</span>
								</label>
							{/each}
						</div>
					</fieldset>

					<fieldset class="space-y-3">
						<legend class="text-sm font-medium text-gray-700 mb-1"
							>{m.rootCausesDetailedClassification()}</legend
						>
						{#each detailedGroups as [groupName, choices]}
							<div class="border border-gray-200 rounded-lg overflow-hidden">
								<div
									class="bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wide"
								>
									{groupName}
								</div>
								<div class="px-3 py-2 flex flex-wrap gap-2">
									{#each choices as choice}
										<label
											class="flex items-center gap-1.5 text-xs bg-white border border-gray-200 px-2.5 py-1.5 rounded-md hover:bg-gray-50 transition-colors cursor-pointer"
											class:!bg-indigo-50={rootCauseDetailed.includes(choice.value)}
											class:!border-indigo-300={rootCauseDetailed.includes(choice.value)}
										>
											<input
												type="checkbox"
												checked={rootCauseDetailed.includes(choice.value)}
												onchange={() =>
													(rootCauseDetailed = toggleArrayValue(rootCauseDetailed, choice.value))}
												class="rounded"
											/>
											<span>{choice.shortLabel}</span>
										</label>
									{/each}
								</div>
							</div>
						{/each}
					</fieldset>

					<fieldset class="space-y-2">
						<legend class="text-sm font-medium text-gray-700 mb-1"
							>{m.rootCausesAdditionalClassification()}</legend
						>
						<div class="flex flex-wrap gap-2">
							{#each allChoices.rootCauseAdditional as choice}
								<label
									class="flex items-center gap-1.5 text-xs bg-white border border-gray-200 px-2.5 py-1.5 rounded-md hover:bg-gray-50 transition-colors cursor-pointer"
									class:!bg-indigo-50={rootCauseAdditional.includes(choice.value)}
									class:!border-indigo-300={rootCauseAdditional.includes(choice.value)}
								>
									<input
										type="checkbox"
										checked={rootCauseAdditional.includes(choice.value)}
										onchange={() =>
											(rootCauseAdditional = toggleArrayValue(rootCauseAdditional, choice.value))}
										class="rounded"
									/>
									<span>{choice.label}</span>
								</label>
							{/each}
						</div>
					</fieldset>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<TextField form={_form} field="root_causes_other" label={m.rootCausesOther()} />
						<TextField
							form={_form}
							field="root_cause_addressing_date_time"
							label={m.rootCauseAddressingDateTime()}
							type="datetime-local"
						/>
					</div>
					<MarkdownField
						form={_form}
						field="root_causes_information"
						label={m.rootCausesInformation()}
					/>
				</div>

				<!-- Section 7: Impact Assessment -->
				<div class="dora-section" id="dora-section-7">
					<h2 class="dora-section-header">
						<span class="dora-step">7</span>
						<i class="fa-solid fa-chart-bar"></i>{m.doraImpactAssessment()}
					</h2>

					<label class="flex items-center space-x-2">
						<input
							type="checkbox"
							bind:checked={impactAssessment.hasImpactOnRelevantClients}
							class="rounded"
						/>
						<span class="text-sm font-medium">{safeTranslate('hasImpactOnRelevantClients')}</span>
					</label>

					<div>
						<label class="text-sm font-medium text-gray-700" for="criticalServicesAffected"
							>{safeTranslate('criticalServicesAffected')}</label
						>
						<input
							id="criticalServicesAffected"
							type="text"
							bind:value={impactAssessment.criticalServicesAffected}
							class="input w-full mt-1"
						/>
					</div>

					<!-- Service Impact -->
					<div class="border rounded-lg p-4 space-y-3 bg-gray-50">
						<h3 class="font-medium text-sm">{m.doraServiceImpact()}</h3>
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
							<div>
								<label class="text-sm text-gray-700" for="serviceDowntime"
									>{safeTranslate('serviceDowntime')}</label
								>
								<input
									id="serviceDowntime"
									type="text"
									placeholder="HH:MM:SS"
									bind:value={serviceImpact.serviceDowntime}
									class="input w-full mt-1"
								/>
							</div>
							<div>
								<label class="text-sm text-gray-700" for="serviceRestoration"
									>{safeTranslate('serviceRestorationDateTime')}</label
								>
								<input
									id="serviceRestoration"
									type="datetime-local"
									bind:value={serviceImpact.serviceRestorationDateTime}
									class="input w-full mt-1"
								/>
							</div>
						</div>
					</div>

					<!-- Affected Assets -->
					<div class="border rounded-lg p-4 space-y-3 bg-gray-50">
						<h3 class="font-medium text-sm">{m.doraAffectedAssets()}</h3>
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-xs text-gray-500">
									<th class="py-1 pr-4"></th>
									<th class="py-1 px-2">{m.number()}</th>
									<th class="py-1 px-2">{m.percentage()}</th>
								</tr>
							</thead>
							<tbody>
								{#each [{ key: 'affectedClients', label: m.affectedClientsLabel() }, { key: 'affectedFinancialCounterparts', label: m.affectedFinancialCounterpartsLabel() }, { key: 'affectedTransactions', label: m.affectedTransactionsLabel() }] as item}
									<tr>
										<td class="py-2 pr-4 font-medium whitespace-nowrap">{item.label}</td>
										<td class="py-2 px-2">
											<input
												id="{item.key}-number"
												type="number"
												bind:value={affectedAssets[item.key].number}
												class="input w-full"
											/>
										</td>
										<td class="py-2 px-2">
											<input
												id="{item.key}-pct"
												type="number"
												step="0.01"
												min="0"
												max="100"
												bind:value={affectedAssets[item.key].percentage}
												class="input w-full"
											/>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
						<div class="grid grid-cols-2 gap-4">
							<div>
								<label class="text-sm text-gray-700" for="txValue"
									>{safeTranslate('valueOfAffectedTransactions')}</label
								>
								<input
									id="txValue"
									type="number"
									step="0.01"
									bind:value={affectedAssets.valueOfAffectedTransactions}
									class="input w-full mt-1"
								/>
							</div>
						</div>
					</div>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div>
							<label class="text-sm text-gray-700" for="affectedFunctionalAreas"
								>{safeTranslate('affectedFunctionalAreas')}</label
							>
							<input
								id="affectedFunctionalAreas"
								type="text"
								bind:value={impactAssessment.affectedFunctionalAreas}
								class="input w-full mt-1"
							/>
						</div>
						<div>
							<label class="text-sm text-gray-700" for="infraComponents"
								>{safeTranslate('isAffectedInfrastructureComponents')}</label
							>
							<select
								id="infraComponents"
								bind:value={impactAssessment.isAffectedInfrastructureComponents}
								class="select w-full mt-1"
							>
								<option value="">--</option>
								<option value="yes">{m.yes()}</option>
								<option value="no">{m.no()}</option>
								<option value="information_not_available">{m.informationNotAvailable()}</option>
							</select>
						</div>
					</div>

					{#if impactAssessment.isAffectedInfrastructureComponents === 'yes'}
						<div>
							<label class="text-sm text-gray-700" for="infraDesc"
								>{safeTranslate('affectedInfrastructureComponents')}</label
							>
							<textarea
								id="infraDesc"
								bind:value={impactAssessment.affectedInfrastructureComponents}
								class="textarea w-full mt-1"
								rows="2"
							></textarea>
						</div>
					{/if}
				</div>

				<!-- Section 8: Resolution & Financial -->
				<div class="dora-section" id="dora-section-8">
					<h2 class="dora-section-header">
						<span class="dora-step">8</span>
						<i class="fa-solid fa-coins"></i>{m.doraResolutionAndFinancial()}
					</h2>
					<MarkdownField
						form={_form}
						field="incident_resolution_vs_planned"
						label={m.incidentResolutionVsPlanned()}
					/>
					<MarkdownField
						form={_form}
						field="assessment_of_risk_to_critical_functions"
						label={m.assessmentOfRiskToCriticalFunctions()}
					/>
					<MarkdownField
						form={_form}
						field="information_relevant_to_resolution_authorities"
						label={m.informationRelevantToResolutionAuthorities()}
					/>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<TextField
							form={_form}
							field="financial_recoveries_amount"
							label={m.financialRecoveriesAmount()}
							type="number"
						/>
						<TextField
							form={_form}
							field="gross_amount_indirect_direct_costs"
							label={m.grossAmountIndirectDirectCosts()}
							type="number"
						/>
					</div>
				</div>

				<!-- Section 9: Reporting & Recurring -->
				<div class="dora-section" id="dora-section-9">
					<h2 class="dora-section-header">
						<span class="dora-step">9</span>
						<i class="fa-solid fa-bullhorn"></i>{m.doraReportingAndRecurring()}
					</h2>

					<fieldset class="space-y-2">
						<legend class="text-sm font-medium text-gray-700 mb-1"
							>{m.reportingToOtherAuthorities()}</legend
						>
						<div class="flex flex-wrap gap-3">
							{#each allChoices.reportingAuthority as choice}
								<label class="flex items-center space-x-2 text-sm">
									<input
										type="checkbox"
										checked={reportingAuthorities.includes(choice.value)}
										onchange={() =>
											(reportingAuthorities = toggleArrayValue(reportingAuthorities, choice.value))}
										class="rounded"
									/>
									<span>{choice.label}</span>
								</label>
							{/each}
						</div>
					</fieldset>

					{#if hasOtherAuthority}
						<TextField
							form={_form}
							field="reporting_to_other_authorities_other"
							label={m.reportingToOtherAuthoritiesOther()}
						/>
					{/if}

					<Select
						form={_form}
						options={allChoices.downtimeInfo}
						field="info_duration_service_downtime_actual_or_estimate"
						label={m.infoDurationServiceDowntimeActualOrEstimate()}
					/>

					<MarkdownField
						form={_form}
						field="recurring_non_major_incidents_description"
						label={m.recurringNonMajorIncidentsDescription()}
					/>
					<TextField
						form={_form}
						field="recurring_incident_date"
						label={m.recurringIncidentDate()}
						type="datetime-local"
					/>
				</div>
			</fieldset>

			<!-- Sticky Footer -->
			<div
				class="sticky bottom-0 z-10 bg-white/95 backdrop-blur-sm border-t border-gray-200 px-6 py-3 shadow-[0_-4px_16px_rgba(0,0,0,0.06)]"
			>
				{#if isSubmitted}
					<div class="flex items-center justify-between">
						<div></div>
						<div class="flex space-x-3">
							{#if validation?.valid}
								<a
									href="/dora-incident-reports/{reportId}/export/json"
									class="btn preset-filled-primary-500 font-semibold px-6"
								>
									<i class="fa-solid fa-file-code mr-2"></i>{m.asDoraJson()}
								</a>
							{/if}
							{#if canProgress}
								<a
									href="/dora-incident-reports/new?from={reportId}"
									class="btn preset-filled-secondary-500 font-semibold px-6"
								>
									<i class="fa-solid fa-arrow-right mr-2"></i>{m.nextSubmission()}
								</a>
							{/if}
						</div>
					</div>
				{:else}
					<div class="flex justify-between items-center">
						<div class="flex space-x-3">
							{#if mode === 'edit' && reportId}
								{#if validation?.valid}
									<a
										href="/dora-incident-reports/{reportId}/export/json"
										class="btn preset-filled-primary-500 font-semibold px-6"
									>
										<i class="fa-solid fa-file-code mr-2"></i>{m.asDoraJson()}
									</a>
								{:else}
									<span
										class="btn preset-filled-surface-500 font-semibold px-6 opacity-50 cursor-not-allowed"
										title={m.schemaInvalid()}
									>
										<i class="fa-solid fa-file-code mr-2"></i>{m.asDoraJson()}
									</span>
								{/if}
								{#if canProgress}
									<a
										href="/dora-incident-reports/new?from={reportId}"
										class="btn preset-filled-secondary-500 font-semibold px-6"
									>
										<i class="fa-solid fa-arrow-right mr-2"></i>{m.nextSubmission()}
									</a>
								{/if}
							{/if}
						</div>
						<div class="flex space-x-3">
							{#if mode === 'edit' && reportId && !isSubmitted && validation?.valid}
								<button
									type="button"
									class="btn preset-filled-warning-500 font-semibold px-6"
									onclick={modalMarkSubmitted}
								>
									<i class="fa-solid fa-lock mr-2"></i>{m.markAsSubmitted()}
								</button>
							{/if}
							<button
								type="button"
								class="btn preset-filled-tertiary-500 font-semibold px-8"
								onclick={cancel}
							>
								{m.cancel()}
							</button>
							<button type="submit" class="btn preset-filled-primary-500 font-semibold px-8">
								{m.save()}
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/snippet}
	</SuperForm>
</div>

<style>
	.dora-section {
		background: white;
		border-radius: 0.75rem;
		box-shadow:
			0 1px 3px rgba(0, 0, 0, 0.06),
			0 1px 2px rgba(0, 0, 0, 0.04);
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		border-left: 4px solid rgb(99, 102, 241);
		transition: box-shadow 0.15s ease;
	}
	.dora-section:hover {
		box-shadow:
			0 4px 12px rgba(0, 0, 0, 0.08),
			0 2px 4px rgba(0, 0, 0, 0.04);
	}
	.dora-section-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: rgb(49, 46, 129);
		padding-bottom: 0.75rem;
		border-bottom: 1px solid rgb(224, 231, 255);
	}
	.dora-step {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 9999px;
		background: rgb(79, 70, 229);
		color: white;
		font-size: 0.7rem;
		font-weight: 700;
		flex-shrink: 0;
	}
	.dora-section-header i {
		color: rgb(129, 140, 248);
		font-size: 0.85rem;
	}
</style>
