<script lang="ts">
	import { run } from 'svelte/legacy';

	import { setContext, onDestroy } from 'svelte';
	import type { Component } from 'svelte';

	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import LoadingSpinner from '../utils/LoadingSpinner.svelte';

	import AutocompleteSelect from './AutocompleteSelect.svelte';

	import { modelSchema } from '$lib/utils/schemas';
	import type { ModelInfo, urlModel, CacheLock } from '$lib/utils/types';
	import { superForm, superValidate, type SuperValidated } from 'sveltekit-superforms';
	import type { FormDataShape } from '$lib/utils/schemas';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { createModalCache } from '$lib/utils/stores';
	import { goto } from '$lib/utils/breadcrumbs';
	import { safeTranslate } from '$lib/utils/i18n';

	type ModelFormComponent = Component<any>;
	type ModelFormLoader = () => Promise<{ default: ModelFormComponent }>;

	const modelFormLoaders: Record<string, ModelFormLoader> = {
		perimeters: () => import('./ModelForm/PerimeterForm.svelte'),
		folders: () => import('./ModelForm/FolderForm.svelte'),
		'folders-import': () => import('./ModelForm/FolderForm.svelte'),
		'risk-assessments': () => import('./ModelForm/RiskAssessmentForm.svelte'),
		threats: () => import('./ModelForm/ThreatForm.svelte'),
		'security-advisories': () => import('./ModelForm/SecurityAdvisoryForm.svelte'),
		cwes: () => import('./ModelForm/CWEForm.svelte'),
		'risk-scenarios': () => import('./ModelForm/RiskScenarioForm.svelte'),
		'applied-controls': () => import('./ModelForm/AppliedControlPolicyForm.svelte'),
		policies: () => import('./ModelForm/AppliedControlPolicyForm.svelte'),
		vulnerabilities: () => import('./ModelForm/VulnerabilitiesForm.svelte'),
		'risk-acceptances': () => import('./ModelForm/RiskAcceptanceForm.svelte'),
		'validation-flows': () => import('./ModelForm/ValidationFlowForm.svelte'),
		'reference-controls': () => import('./ModelForm/ReferenceControlForm.svelte'),
		evidences: () => import('./ModelForm/EvidenceForm.svelte'),
		'compliance-assessments': () => import('./ModelForm/ComplianceAssessmentForm.svelte'),
		campaigns: () => import('./ModelForm/CampaignForm.svelte'),
		assets: () => import('./ModelForm/AssetForm.svelte'),
		'requirement-assessments': () => import('./ModelForm/RequirementAssessmentForm.svelte'),
		entities: () => import('./ModelForm/EntityForm.svelte'),
		'entity-assessments': () => import('./ModelForm/EntityAssessmentForm.svelte'),
		solutions: () => import('./ModelForm/SolutionForm.svelte'),
		contracts: () => import('./ModelForm/ContractForm.svelte'),
		representatives: () => import('./ModelForm/RepresentativeForm.svelte'),
		frameworks: () => import('./ModelForm/FrameworkForm.svelte'),
		users: () => import('./ModelForm/UserForm.svelte'),
		teams: () => import('./ModelForm/TeamForm.svelte'),
		'sso-settings': () => import('./ModelForm/SsoSettingForm.svelte'),
		'general-settings': () => import('./ModelForm/GeneralSettingForm.svelte'),
		'feature-flags': () => import('./ModelForm/FeatureFlagsSettingForm.svelte'),
		'vulnerability-sla': () => import('./ModelForm/VulnerabilitySlaSettingForm.svelte'),
		'sec-intel-feeds': () => import('./ModelForm/SecIntelFeedsSettingForm.svelte'),
		'filtering-labels': () => import('./ModelForm/FilteringLabelForm.svelte'),
		'business-impact-analysis': () => import('./ModelForm/BusinessImpactAnalysisForm.svelte'),
		'asset-assessments': () => import('./ModelForm/AssetAssessmentForm.svelte'),
		'escalation-thresholds': () => import('./ModelForm/EscalationThresholdForm.svelte'),
		processings: () => import('./ModelForm/ProcessingForm.svelte'),
		purposes: () => import('./ModelForm/PurposeForm.svelte'),
		'personal-data': () => import('./ModelForm/PersonalDataForm.svelte'),
		'data-subjects': () => import('./ModelForm/DataSubjectForm.svelte'),
		'data-recipients': () => import('./ModelForm/DataRecipientForm.svelte'),
		'data-contractors': () => import('./ModelForm/DataContractorForm.svelte'),
		'data-transfers': () => import('./ModelForm/DataTransferForm.svelte'),
		'right-requests': () => import('./ModelForm/RightRequestForm.svelte'),
		'data-breaches': () => import('./ModelForm/DataBreachForm.svelte'),
		'ebios-rm': () => import('./ModelForm/EbiosRmForm.svelte'),
		'feared-events': () => import('./ModelForm/FearedEventForm.svelte'),
		'ro-to': () => import('./ModelForm/RoToForm.svelte'),
		stakeholders: () => import('./ModelForm/StakeholderForm.svelte'),
		'strategic-scenarios': () => import('./ModelForm/StrategicScenarioForm.svelte'),
		'attack-paths': () => import('./ModelForm/AttackPathForm.svelte'),
		'operational-scenarios': () => import('./ModelForm/OperationalScenarioForm.svelte'),
		'security-exceptions': () => import('./ModelForm/SecurityExceptionForm.svelte'),
		findings: () => import('./ModelForm/FindingForm.svelte'),
		'findings-assessments': () => import('./ModelForm/FindingsAssessmentForm.svelte'),
		incidents: () => import('./ModelForm/IncidentForm.svelte'),
		'timeline-entries': () => import('./ModelForm/TimelineEntryForm.svelte'),
		'task-templates': () => import('./ModelForm/TaskTemplateForm.svelte'),
		'task-nodes': () => import('./ModelForm/TaskNodeForm.svelte'),
		'elementary-actions': () => import('./ModelForm/ElementaryActionForm.svelte'),
		'operating-modes': () => import('./ModelForm/OperatingModeForm.svelte'),
		'kill-chains': () => import('./ModelForm/KillChainForm.svelte'),
		'quantitative-risk-studies': () => import('./ModelForm/QuantitativeRiskStudyForm.svelte'),
		'quantitative-risk-scenarios': () => import('./ModelForm/QuantitativeRiskScenarioForm.svelte'),
		'quantitative-risk-hypotheses': () =>
			import('./ModelForm/QuantitativeRiskHypothesisForm.svelte'),
		'organisation-issues': () => import('./ModelForm/OrganisationIssueForm.svelte'),
		'organisation-objectives': () => import('./ModelForm/OrganisationObjectiveForm.svelte'),
		terminologies: () => import('./ModelForm/TerminologyForm.svelte'),
		roles: () => import('./ModelForm/RoleForm.svelte'),
		'evidence-revisions': () => import('./ModelForm/EvidenceRevisionForm.svelte'),
		'generic-collections': () => import('./ModelForm/GenericCollectionForm.svelte'),
		accreditations: () => import('./ModelForm/AccreditationForm.svelte'),
		projects: () => import('./ModelForm/ProjectForm.svelte'),
		'responsibility-matrices': () => import('./ModelForm/ResponsibilityMatrixForm.svelte'),
		'responsibility-matrix-activities': () =>
			import('./ModelForm/ResponsibilityMatrixActivityForm.svelte'),
		'responsibility-assignments': () => import('./ModelForm/ResponsibilityAssignmentForm.svelte'),
		'responsibility-roles': () => import('./ModelForm/ResponsibilityRoleForm.svelte'),
		'metric-definitions': () => import('./ModelForm/MetricDefinitionForm.svelte'),
		'metric-instances': () => import('./ModelForm/MetricInstanceForm.svelte'),
		'custom-metric-samples': () => import('./ModelForm/CustomMetricSampleForm.svelte'),
		dashboards: () => import('./ModelForm/DashboardForm.svelte'),
		'dashboard-widgets': () => import('./ModelForm/DashboardWidgetForm.svelte'),
		'dashboard-text-widgets': () => import('./ModelForm/DashboardTextWidgetForm.svelte'),
		'dashboard-builtin-widgets': () => import('./ModelForm/DashboardBuiltinWidgetForm.svelte')
	};

	interface Props {
		form: SuperValidated<FormDataShape>;
		invalidateAll?: boolean; // set to false to keep form data using muliple forms on a page
		taintedMessage?: string | boolean;
		model: ModelInfo;
		context?: string;
		origin?: string | null;
		caching?: boolean;
		closeModal?: boolean;
		parent?: any;
		suggestions?: { [key: string]: any };
		cancelButton?: boolean;
		duplicate?: boolean;
		importFolder?: boolean;
		customNameDescription?: boolean;
		additionalInitialData?: any;
		schema?: any;
		object?: Record<string, any>;
		[key: string]: any;
	}

	let {
		form,
		invalidateAll = true,
		taintedMessage = m.taintedFormMessage(),
		model,
		context = 'default',
		origin = null,
		caching = false,
		closeModal = false,
		parent = {},
		suggestions = {},
		cancelButton = true,
		duplicate = false,
		importFolder = false,
		customNameDescription = false,
		additionalInitialData = {},
		schema = modelSchema(model.urlModel),
		object = {},
		...rest
	}: Props = $props();

	const URLModel = model.urlModel as urlModel;
	const modelFormPromise = modelFormLoaders[URLModel]?.();
	const defaultFolderWritePermission =
		context === 'edit' ? `change_${model.name}` : `add_${model.name}`;
	setContext('folderTreeDefaultWritePermission', defaultFolderWritePermission);

	function getModelFormProps(slotForm: any, data: any, initialData: any) {
		const base = { form: slotForm, model, cacheLocks, formDataCache };
		const dashboardBase = { form: slotForm, cacheLocks, formDataCache };
		const mergedInitialData = { ...initialData, ...additionalInitialData };
		const withInitialData = { ...base, initialData };
		const withContext = { ...base, context };
		const withObject = { ...base, object };
		const withInitialDataAndContext = { ...withInitialData, context };
		const withInitialDataAndObject = { ...withInitialData, object };
		const withInitialDataObjectContext = { ...withInitialDataAndObject, context };
		const withModelInitialData = { ...base, initialData: model.initialData };
		const withModelInitialDataAndContext = { ...withModelInitialData, context };
		const withModelInitialDataObjectContext = { ...withModelInitialData, object, context };
		const withMergedInitialData = { ...base, initialData: mergedInitialData };

		switch (URLModel) {
			case 'perimeters':
			case 'organisation-issues':
			case 'organisation-objectives':
				return withInitialData;
			case 'folders':
			case 'folders-import':
				return { ...base, importFolder, initialData, object, ...rest };
			case 'risk-assessments':
			case 'business-impact-analysis':
				return {
					...withInitialDataAndObject,
					duplicate,
					context,
					updated_fields,
					...rest
				};
			case 'threats':
			case 'security-advisories':
			case 'cwes':
			case 'risk-scenarios':
			case 'vulnerabilities':
			case 'reference-controls':
			case 'solutions':
			case 'contracts':
			case 'feared-events':
				return { ...withInitialData, ...rest };
			case 'applied-controls':
			case 'policies':
				return {
					...withInitialData,
					duplicate,
					schema,
					origin,
					context,
					...rest
				};
			case 'risk-acceptances':
			case 'validation-flows':
			case 'entities':
				return { ...withInitialDataAndObject, ...rest };
			case 'evidences':
			case 'compliance-assessments':
			case 'campaigns':
			case 'entity-assessments':
			case 'operational-scenarios':
				return { ...withInitialDataObjectContext, ...rest };
			case 'assets':
				return { ...withInitialDataAndObject, data, ...rest };
			case 'requirement-assessments':
			case 'processings':
			case 'ebios-rm':
			case 'stakeholders':
			case 'task-nodes':
				return { ...withContext, ...rest };
			case 'representatives':
				return { ...withObject, context, ...rest };
			case 'frameworks':
			case 'filtering-labels':
				return { ...base, ...rest };
			case 'users':
			case 'teams':
				return { ...withContext, shape, ...rest };
			case 'sso-settings':
			case 'general-settings':
			case 'feature-flags':
				return { ...base, data, ...rest };
			case 'vulnerability-sla':
			case 'sec-intel-feeds':
				return { form: slotForm, model };
			case 'asset-assessments':
			case 'escalation-thresholds':
			case 'personal-data':
			case 'data-subjects':
			case 'data-recipients':
			case 'data-contractors':
			case 'data-transfers':
			case 'right-requests':
			case 'data-breaches':
			case 'strategic-scenarios':
			case 'security-exceptions':
			case 'findings':
			case 'findings-assessments':
			case 'incidents':
			case 'task-templates':
			case 'elementary-actions':
			case 'purposes':
			case 'ro-to':
				return { ...withInitialDataAndContext, ...rest };
			case 'attack-paths':
				return { ...withInitialData, additionalInitialData, ...rest };
			case 'timeline-entries':
			case 'operating-modes':
				return { ...withModelInitialDataAndContext, ...rest };
			case 'kill-chains':
				return { ...withModelInitialDataObjectContext, ...rest };
			case 'quantitative-risk-studies':
			case 'quantitative-risk-scenarios':
			case 'quantitative-risk-hypotheses':
				return { ...withInitialDataObjectContext, duplicate };
			case 'terminologies':
				return withInitialDataAndObject;
			case 'roles':
				return withContext;
			case 'evidence-revisions':
			case 'generic-collections':
			case 'responsibility-matrices':
			case 'responsibility-matrix-activities':
			case 'responsibility-assignments':
				return withInitialDataObjectContext;
			case 'accreditations':
			case 'projects':
			case 'responsibility-roles':
				return withInitialDataAndObject;
			case 'metric-definitions':
				return { ...withInitialData, data, ...rest };
			case 'metric-instances':
				return { ...withMergedInitialData, data, ...rest };
			case 'custom-metric-samples':
				return { ...withMergedInitialData, data, object, ...rest };
			case 'dashboards':
				return { ...dashboardBase, initialData: mergedInitialData, ...rest };
			case 'dashboard-widgets':
			case 'dashboard-builtin-widgets':
				return { ...withMergedInitialData, object, ...rest };
			case 'dashboard-text-widgets':
				return { ...withMergedInitialData, data, object };
			default:
				return { form: slotForm };
		}
	}

	function cancel(): void {
		if (browser) {
			var currentUrl = window.location.href;
			var url = new URL(currentUrl);
			var nextValue = getSecureRedirect(url.searchParams.get('next'));
			if (nextValue) goto(nextValue);
		}
	}
	let shape = $derived(schema.shape || schema._def?.schema?.shape);
	let updated_fields = new Set();

	function makeCacheLock(): CacheLock {
		let resolve: (_: any) => any = (_) => _;
		const promise = new Promise((res) => {
			resolve = res;
		});
		return { resolve, promise };
	}

	let cacheLocks = $state({});
	run(() => {
		if (shape)
			cacheLocks = Object.keys(shape).reduce((acc, field) => {
				acc[field] = makeCacheLock();
				return acc;
			}, {});
	});

	let formDataCache = $state({});
	let urlModelFromPage = $state();

	run(() => {
		if ($page) {
			urlModelFromPage = `${$page.url}`.replace(/^.*:\/\/[^/]+/, '');
			createModalCache.setModelName(urlModelFromPage);
			if (caching) {
				const currentCache = createModalCache.data[model.urlModel];
				if (!currentCache) {
					createModalCache.data[model.urlModel] = formDataCache;
				} else {
					formDataCache = currentCache;
				}
			}
		}
	});

	$effect(() => {
		createModalCache.data[model.urlModel] = formDataCache;
	});

	run(() => {
		if (caching) {
			for (const key of Object.keys(cacheLocks)) {
				cacheLocks[key].resolve(formDataCache[key]);
			}
		}
	});

	let missingConstraints: string[] = $state([]);
	// Context function to update missing constraints
	function updateMissingConstraint(field: string, isMissing: boolean) {
		if (isMissing && !missingConstraints.includes(field)) {
			missingConstraints = [...missingConstraints, field];
		} else if (!isMissing) {
			missingConstraints = missingConstraints.filter((f) => f !== field);
		}
	}
	setContext('updateMissingConstraint', updateMissingConstraint);

	onDestroy(() => {
		missingConstraints = [];
		createModalCache.garbageCollect();
	});

	const _form = superForm(form, {
		dataType: shape?.attachment ? 'form' : 'json',
		enctype: shape?.attachment ? 'multipart/form-data' : 'application/x-www-form-urlencoded',
		invalidateAll,
		applyAction: rest.applyAction ?? true,
		resetForm: rest.resetForm ?? false,
		validators: zod(schema),
		taintedMessage,
		validationMethod: 'auto',
		onUpdated: async ({ form }) => {
			if (form.message?.redirect) {
				goto(getSecureRedirect(form.message.redirect));
			}
			if (form.valid && !form.message?.error) {
				if (parent && typeof parent.onConfirm === 'function') {
					parent.onConfirm();
				}
				createModalCache.deleteCache(model.urlModel);
			}
		}
	});

	let isLoading = $state(false);
	let previousFormErrors = $derived('');
	const { form: formData, errors } = _form;

	errors.subscribe((newErrors) => {
		const errorCount = Object.values(newErrors).reduce((acc, error) => (acc += error ? 1 : 0), 0);
		const stringifiedErrors = JSON.stringify([Date.now(), newErrors]);

		if (errorCount && stringifiedErrors !== previousFormErrors) {
			isLoading = false;
			previousFormErrors = stringifiedErrors;
		}
	});
</script>

{#if missingConstraints.length > 0}
	<div class="mb-4 p-4 bg-red-100 text-red-700 rounded-lg">
		{m.missingMandatoyObjects1({ model: safeTranslate(model.localName) })}:
		{#each missingConstraints as key}
			<li class="font-bold">{safeTranslate(key)}</li>
		{/each}
		{m.missingMandatoyObjects2()}
	</div>
{/if}
<SuperForm
	class="flex flex-col space-y-3"
	dataType={shape.attachment ? 'form' : 'json'}
	enctype={shape.attachment ? 'multipart/form-data' : 'application/x-www-form-urlencoded'}
	data={form}
	{_form}
	{invalidateAll}
	validators={zod(schema)}
	onUpdated={() => createModalCache.deleteCache(model.urlModel)}
	{...rest}
>
	{#snippet children({ form, data, initialData })}
		<input type="hidden" name="urlmodel" value={model.urlModel} />
		{#if additionalInitialData?.genericcollection}
			<input
				type="hidden"
				name="genericcollection"
				value={additionalInitialData.genericcollection}
			/>
		{/if}
		<!--NOTE: Not the cleanest pattern, will refactor-->
		<!--TODO: Refactor-->
		{#if shape.reference_control && !duplicate}
			<AutocompleteSelect
				{form}
				optionsEndpoint="reference-controls"
				optionsExtraFields={[['folder', 'str']]}
				optionsLabelField="auto"
				optionsSuggestions={suggestions['reference_control']}
				field="reference_control"
				cacheLock={cacheLocks['reference_control']}
				bind:cachedValue={formDataCache['reference_control']}
				label={m.referenceControl()}
				helpText={m.referenceControlHelpText()}
				nullable={true}
				onChange={async (e) => {
					if (e) {
						await fetch(`/reference-controls/${e}`)
							.then((r) => r.json())
							.then((r) => {
								form.form.update((currentData) => {
									if (
										context === 'edit' &&
										currentData['reference_control'] === initialData['reference_control'] &&
										!updated_fields.has('reference_control')
									) {
										return currentData; // Keep the current values in the edit form.
									}
									updated_fields.add('reference_control');
									// Only auto-fill name if it's empty OR user hasn't manually edited it
									const shouldUpdateName = !currentData.name || !updated_fields.has('name');
									return {
										...currentData,
										name: shouldUpdateName ? r.name : currentData.name,
										category: r.category,
										csf_function: r.csf_function,
										ref_id: r.ref_id ?? currentData.ref_id ?? ''
									};
								});
							});
					}
				}}
			/>
		{/if}
		{#if shape.name && !customNameDescription}
			<TextField
				{form}
				field="name"
				label={m.name()}
				cacheLock={cacheLocks['name']}
				bind:cachedValue={formDataCache['name']}
				data-focusindex="0"
				oninput={() => {
					updated_fields.add('name');
				}}
			/>
		{/if}
		{#if shape.description && !customNameDescription}
			<MarkdownField
				{form}
				field="description"
				label={m.description()}
				cacheLock={cacheLocks['description']}
				bind:cachedValue={formDataCache['description']}
				data-focusindex="1"
			/>
		{/if}
		{#if modelFormPromise}
			{#await modelFormPromise}
				<div class="flex justify-center py-4">
					<LoadingSpinner />
				</div>
			{:then modelFormModule}
				{@const ModelSpecificForm = modelFormModule.default}
				<ModelSpecificForm {...getModelFormProps(form, data, initialData)} />
			{:catch error}
				<p class="text-red-600 text-sm">Unable to load form: {error?.message ?? error}</p>
			{/await}
		{/if}
		<div
			class="flex flex-row justify-between space-x-4 sticky bottom-0 backdrop-blur-sm pt-4 pb-2 border-t border-slate-200"
		>
			{#if closeModal}
				<button
					class="btn bg-gray-400 text-white font-semibold w-full"
					data-testid="cancel-button"
					type="button"
					onclick={(event) => {
						parent.onClose(event);
						createModalCache.deleteCache(model.urlModel);
					}}>{m.cancel()}</button
				>
				<button
					class="btn preset-filled-primary-500 font-semibold w-full {isLoading
						? 'cursor-wait'
						: ''}"
					data-testid="save-button"
					type="submit"
					onclick={(e) => {
						if (URLModel !== 'folders-import') return;
						if (isLoading) {
							e.preventDefault();
							e.stopPropagation();
							return;
						}

						const schema = modelSchema(URLModel);
						const result = schema.safeParse($formData);
						if (!result.success) return;

						isLoading = true;
					}}
					>{#if isLoading}{m.loading()} <LoadingSpinner />{:else}{m.save()}{/if}</button
				>
			{:else}
				{#if cancelButton}
					<button
						class="btn bg-gray-400 text-white font-semibold w-full"
						data-testid="cancel-button"
						type="button"
						onclick={cancel}>{m.cancel()}</button
					>
				{/if}
				<button
					class="btn preset-filled-primary-500 font-semibold w-full"
					data-testid="save-button"
					type="submit">{m.save()}</button
				>
			{/if}
		</div>
	{/snippet}
</SuperForm>
