<script lang="ts">
	import { onDestroy } from 'svelte';

	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';

	import RiskAssessmentForm from './ModelForm/RiskAssessmentForm.svelte';
	import ProjectForm from './ModelForm/ProjectForm.svelte';
	import ThreatForm from './ModelForm/ThreatForm.svelte';
	import RiskScenarioForm from './ModelForm/RiskScenarioForm.svelte';
	import AppliedControlsPoliciesForm from './ModelForm/AppliedControlPolicyForm.svelte';
	import RiskAcceptancesForm from './ModelForm/RiskAcceptanceForm.svelte';
	import ReferenceControlsForm from './ModelForm/ReferenceControlForm.svelte';
	import EvidencesForm from './ModelForm/EvidenceForm.svelte';
	import ComplianceAssessmentsForm from './ModelForm/ComplianceAssessmentForm.svelte';
	import AssetsForm from './ModelForm/AssetForm.svelte';
	import RequirementAssessmentsForm from './ModelForm/RequirementAssessmentForm.svelte';
	import EntitiesForm from './ModelForm/EntityForm.svelte';
	import EntityAssessmentForm from './ModelForm/EntityAssessmentForm.svelte';
	import SolutionsForm from './ModelForm/SolutionForm.svelte';
	import RepresentativesForm from './ModelForm/RepresentativeForm.svelte';
	import FrameworksForm from './ModelForm/FrameworkForm.svelte';
	import UsersForm from './ModelForm/UserForm.svelte';
	import SsoSettingsForm from './ModelForm/SsoSettingForm.svelte';
	import GeneralSettingsForm from './ModelForm/GeneralSettingForm.svelte';

	import AutocompleteSelect from './AutocompleteSelect.svelte';

	import { getOptions } from '$lib/utils/crud';
	import { modelSchema } from '$lib/utils/schemas';
	import type { ModelInfo, urlModel, CacheLock } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages.js';
	import { zod } from 'sveltekit-superforms/adapters';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { createModalCache } from '$lib/utils/stores';

	export let form: SuperValidated<AnyZodObject>;
	export let invalidateAll = true; // set to false to keep form data using muliple forms on a page
	export let model: ModelInfo;
	export let context = 'default';
	export let caching: boolean = false;
	export let closeModal = false;
	export let parent: any;
	export let suggestions: { [key: string]: any } = {};
	export let cancelButton = true;
	export let riskAssessmentDuplication = false;

	const URLModel = model.urlModel as urlModel;
	export let schema = modelSchema(URLModel);
	export let object: Record<string, any> = {};

	function cancel(): void {
		if (browser) {
			var currentUrl = window.location.href;
			var url = new URL(currentUrl);
			var nextValue = getSecureRedirect(url.searchParams.get('next'));
			if (nextValue) window.location.href = nextValue;
		}
	}
	$: shape = schema.shape || schema._def.schema.shape;
	let updated_fields = new Set();

	function makeCacheLock(): CacheLock {
		let resolve: (_: any) => any = (_) => _;
		const promise = new Promise((res) => {
			resolve = res;
		});
		return { resolve, promise };
	}

	let cacheLocks = {};
	$: if (shape)
		cacheLocks = Object.keys(shape).reduce((acc, field) => {
			acc[field] = makeCacheLock();
			return acc;
		}, {});

	let formDataCache = {};
	let urlModelFromPage;

	$: if ($page) {
		urlModelFromPage = `${$page.url}`.replace(/^.*:\/\/[^/]+/, '');
		createModalCache.setModelName(urlModelFromPage);
		if (caching) {
			createModalCache.data[model.urlModel] ??= {};
			formDataCache = createModalCache.data[model.urlModel];
		}
	}

	$: if (caching) {
		for (const key of Object.keys(cacheLocks)) {
			cacheLocks[key].resolve(formDataCache[key]);
		}
	}

	onDestroy(() => {
		createModalCache.garbageCollect();
	});
</script>

<SuperForm
	class="flex flex-col space-y-3"
	dataType={shape.attachment ? 'form' : 'json'}
	enctype={shape.attachment ? 'multipart/form-data' : 'application/x-www-form-urlencoded'}
	data={form}
	{invalidateAll}
	let:form
	let:data
	let:initialData
	validators={zod(schema)}
	onUpdated={() => createModalCache.deleteCache(model.urlModel)}
	{...$$restProps}
>
	<input type="hidden" name="urlmodel" value={model.urlModel} />
	<!--NOTE: Not the cleanest pattern, will refactor-->
	<!--TODO: Refactor-->
	{#if shape.reference_control}
		<AutocompleteSelect
			{form}
			options={getOptions({
				objects: model.foreignKeys['reference_control'],
				extra_fields: [['folder', 'str']],
				suggestions: suggestions['reference_control'],
				label: 'auto' // convention for automatic label calculation
			})}
			field="reference_control"
			cacheLock={cacheLocks['reference_control']}
			bind:cachedValue={formDataCache['reference_control']}
			label={m.referenceControl()}
			nullable={true}
			on:change={async (e) => {
				if (e.detail) {
					await fetch(`/reference-controls/${e.detail}`)
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
								return { ...currentData, category: r.category, csf_function: r.csf_function };
							});
						});
				}
			}}
		/>
	{/if}
	{#if shape.name}
		<TextField
			{form}
			field="name"
			label={m.name()}
			cacheLock={cacheLocks['name']}
			bind:cachedValue={formDataCache['name']}
			data-focusindex="0"
		/>
	{/if}
	{#if shape.description}
		<TextArea
			{form}
			field="description"
			label={m.description()}
			cacheLock={cacheLocks['description']}
			bind:cachedValue={formDataCache['description']}
			data-focusindex="1"
		/>
	{/if}
	{#if URLModel === 'projects'}
		<ProjectForm {form} {model} {cacheLocks} {formDataCache} {initialData} />
	{:else if URLModel === 'risk-assessments' || URLModel === 'risk-assessment-duplicate'}
		<RiskAssessmentForm
			{form}
			{model}
			{riskAssessmentDuplication}
			{cacheLocks}
			{formDataCache}
			{initialData}
			{object}
			{context}
			{updated_fields}
		/>
	{:else if URLModel === 'threats'}
		<ThreatForm {form} {model} {cacheLocks} {formDataCache} {initialData} />
	{:else if URLModel === 'risk-scenarios'}
		<RiskScenarioForm {form} {model} {cacheLocks} {formDataCache} {initialData} />
	{:else if URLModel === 'applied-controls' || URLModel === 'policies'}
		<AppliedControlsPoliciesForm
			{form}
			{model}
			{cacheLocks}
			{formDataCache}
			{schema}
			{initialData}
		/>
	{:else if URLModel === 'risk-acceptances'}
		<RiskAcceptancesForm
			{form}
			{model}
			{cacheLocks}
			{formDataCache}
			{object}
			{initialData}
			{$page}
		/>
	{:else if URLModel === 'reference-controls'}
		<ReferenceControlsForm {form} {model} {cacheLocks} {formDataCache} {initialData} />
	{:else if URLModel === 'evidences'}
		<EvidencesForm {form} {model} {cacheLocks} {formDataCache} {initialData} {object} />
	{:else if URLModel === 'compliance-assessments'}
		<ComplianceAssessmentsForm
			{form}
			{model}
			{cacheLocks}
			{formDataCache}
			{initialData}
			{object}
			{context}
		/>
	{:else if URLModel === 'assets'}
		<AssetsForm {form} {model} {cacheLocks} {formDataCache} {initialData} {object} {data} />
	{:else if URLModel === 'requirement-assessments'}
		<RequirementAssessmentsForm {form} {model} {cacheLocks} {formDataCache} />
	{:else if URLModel === 'entities'}
		<EntitiesForm {form} {model} {cacheLocks} {formDataCache} {initialData} />
	{:else if URLModel === 'entity-assessments'}
		<EntityAssessmentForm {form} {model} {cacheLocks} {formDataCache} {initialData} {data} />
	{:else if URLModel === 'solutions'}
		<SolutionsForm {form} {model} {cacheLocks} {formDataCache} {initialData} />
	{:else if URLModel === 'representatives'}
		<RepresentativesForm {form} {model} {cacheLocks} {formDataCache} {data} />
	{:else if URLModel === 'frameworks'}
		<FrameworksForm {form} {model} {cacheLocks} {formDataCache} />
	{:else if URLModel === 'users'}
		<UsersForm {form} {model} {cacheLocks} {formDataCache} {shape} />
	{:else if URLModel === 'sso-settings'}
		<SsoSettingsForm {form} {model} {cacheLocks} {formDataCache} {data} />
	{:else if URLModel === 'general-settings'}
		<GeneralSettingsForm {form} {model} {cacheLocks} {formDataCache} {data} />
	{/if}
	<div class="flex flex-row justify-between space-x-4">
		{#if closeModal}
			<button
				class="btn bg-gray-400 text-white font-semibold w-full"
				data-testid="cancel-button"
				type="button"
				on:click={(event) => {
					parent.onClose(event);
					createModalCache.deleteCache(model.urlModel);
				}}>{m.cancel()}</button
			>
			<button
				class="btn variant-filled-primary font-semibold w-full"
				data-testid="save-button"
				type="submit"
				on:click={(event) => {
					createModalCache.deleteCache(model.urlModel);
				}}>{m.save()}</button
			>
		{:else}
			{#if cancelButton}
				<button
					class="btn bg-gray-400 text-white font-semibold w-full"
					data-testid="cancel-button"
					type="button"
					on:click={cancel}>{m.cancel()}</button
				>
			{/if}
			<button
				class="btn variant-filled-primary font-semibold w-full"
				data-testid="save-button"
				type="submit">{m.save()}</button
			>
		{/if}
	</div>
</SuperForm>
