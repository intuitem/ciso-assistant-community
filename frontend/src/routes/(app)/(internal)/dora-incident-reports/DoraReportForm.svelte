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

	let incidentType: Record<string, any> = $state(initCopy($formData.incident_type || {}));
	let classificationTypes: Record<string, any>[] = $state(
		initCopy($formData.classification_types || [])
	);
	let impactAssessment: Record<string, any> = $state(
		initCopy({
			serviceImpact: {},
			affectedAssets: {
				affectedClients: {},
				affectedFinancialCounterparts: {},
				affectedTransactions: {}
			},
			...$formData.impact_assessment
		})
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
	{#if incidentRef}
		<div class="flex items-center gap-2 mb-4 text-sm">
			<i class="fa-solid fa-arrow-left text-gray-400"></i>
			<Anchor
				class="anchor font-semibold hover:text-primary-500"
				href="/incidents/{incidentRef.id}"
				prefixCrumbs={[{ label: safeTranslate('incidents'), href: '/incidents' }]}
			>
				<i class="fa-solid fa-bolt mr-1"></i>{incidentRef.name}
			</Anchor>
		</div>
	{/if}
	<h1 class="text-2xl font-bold mb-4">
		{mode === 'create' ? safeTranslate('add-doraIncidentReport') : m.edit()}
	</h1>

	{#if validation && mode === 'edit'}
		<div class="mb-6">
			{#if validation.valid}
				<div class="flex items-center space-x-2 text-green-700 bg-green-50 p-3 rounded-md">
					<i class="fa-solid fa-check-circle text-lg"></i>
					<span class="font-medium">{m.schemaValid()}</span>
				</div>
			{:else}
				<div class="bg-amber-50 p-3 rounded-md space-y-2">
					<div class="flex items-center space-x-2 text-amber-700">
						<i class="fa-solid fa-triangle-exclamation text-lg"></i>
						<span class="font-medium">{m.schemaInvalid()}</span>
					</div>
					{#if validation.errors && validation.errors.length > 0}
						<ul class="list-disc list-inside text-sm text-amber-800 space-y-1 ml-2">
							{#each validation.errors.slice(0, 10) as error}
								<li class="font-mono text-xs">{error}</li>
							{/each}
							{#if validation.errors.length > 10}
								<li class="italic">... and {validation.errors.length - 10} more</li>
							{/if}
						</ul>
					{/if}
				</div>
			{/if}
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-file-lines mr-2"></i>{m.doraReportMetadata()}
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-building mr-2"></i>{m.doraEntitiesAndContacts()}
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-circle-info mr-2"></i>{m.doraIncidentDetails()}
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-tag mr-2"></i>{m.doraIncidentType()}
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-list-check mr-2"></i>{m.doraClassificationCriteria()}
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-magnifying-glass mr-2"></i>{m.doraRootCauseAnalysis()}
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

					<fieldset class="space-y-2">
						<legend class="text-sm font-medium text-gray-700 mb-1"
							>{m.rootCausesDetailedClassification()}</legend
						>
						<div class="flex flex-wrap gap-2">
							{#each allChoices.rootCauseDetailed as choice}
								<label class="flex items-center space-x-1 text-xs bg-gray-100 px-2 py-1 rounded-md">
									<input
										type="checkbox"
										checked={rootCauseDetailed.includes(choice.value)}
										onchange={() =>
											(rootCauseDetailed = toggleArrayValue(rootCauseDetailed, choice.value))}
										class="rounded"
									/>
									<span>{choice.label}</span>
								</label>
							{/each}
						</div>
					</fieldset>

					<fieldset class="space-y-2">
						<legend class="text-sm font-medium text-gray-700 mb-1"
							>{m.rootCausesAdditionalClassification()}</legend
						>
						<div class="flex flex-wrap gap-2">
							{#each allChoices.rootCauseAdditional as choice}
								<label class="flex items-center space-x-1 text-xs bg-gray-100 px-2 py-1 rounded-md">
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-chart-bar mr-2"></i>{m.doraImpactAssessment()}
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-coins mr-2"></i>{m.doraResolutionAndFinancial()}
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
				<div class="card bg-white shadow-md p-6 space-y-4">
					<h2 class="text-lg font-semibold border-b pb-2">
						<i class="fa-solid fa-bullhorn mr-2"></i>{m.doraReportingAndRecurring()}
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
			<div class="sticky bottom-0 z-10 bg-white border-t p-4 shadow-lg rounded-t-lg space-y-3">
				{#if isSubmitted}
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2 text-blue-700 bg-blue-50 px-4 py-2 rounded-md">
							<i class="fa-solid fa-lock text-lg"></i>
							<span class="font-medium">{m.submittedReport()}</span>
						</div>
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
