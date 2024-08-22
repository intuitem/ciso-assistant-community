<script lang="ts">
	import { onDestroy } from 'svelte';

	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';

	import AutocompleteSelect from './AutocompleteSelect.svelte';
	import Select from './Select.svelte';

	import { getOptions } from '$lib/utils/crud';
	import { modelSchema } from '$lib/utils/schemas';
	import type { ModelInfo, urlModel, CacheLock } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import HiddenInput from './HiddenInput.svelte';
	import FileInput from './FileInput.svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages.js';
	import { zod } from 'sveltekit-superforms/adapters';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import { createModalCache } from '$lib/utils/stores';
	import Score from './Score.svelte';
	export let form: SuperValidated<AnyZodObject>;
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
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hide={initialData.folder}
		/>
		<TextField
			{form}
			field="internal_reference"
			label={m.internalReference()}
			cacheLock={cacheLocks['internal_reference']}
			bind:cachedValue={formDataCache['internal_reference']}
		/>
		<Select
			{form}
			options={model.selectOptions['lc_status']}
			field="lc_status"
			label={m.lcStatus()}
			cacheLock={cacheLocks['lc_status']}
			bind:cachedValue={formDataCache['lc_status']}
		/>
	{:else if URLModel === 'risk-assessments' || URLModel === 'risk-assessment-duplicate'}
		<AutocompleteSelect
			{form}
			options={getOptions({
				objects: model.foreignKeys['project'],
				extra_fields: [['folder', 'str']]
			})}
			field="project"
			cacheLock={cacheLocks['project']}
			bind:cachedValue={formDataCache['project']}
			label={m.project()}
			hide={initialData.project}
		/>
		<TextField
			{form}
			field="version"
			label={m.version()}
			cacheLock={cacheLocks['version']}
			bind:cachedValue={formDataCache['version']}
		/>
		{#if !riskAssessmentDuplication}
			<Select
				{form}
				options={model.selectOptions['status']}
				field="status"
				hide
				label={m.status()}
				cacheLock={cacheLocks['status']}
				bind:cachedValue={formDataCache['status']}
			/>
			<AutocompleteSelect
				{form}
				disabled={object.id}
				options={getOptions({ objects: model.foreignKeys['risk_matrix'] })}
				field="risk_matrix"
				cacheLock={cacheLocks['risk_matrix']}
				bind:cachedValue={formDataCache['risk_matrix']}
				label={m.riskMatrix()}
				helpText={m.riskAssessmentMatrixHelpText()}
			/>
			<AutocompleteSelect
				{form}
				multiple
				options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
				field="authors"
				cacheLock={cacheLocks['authors']}
				bind:cachedValue={formDataCache['authors']}
				label={m.authors()}
			/>
			<AutocompleteSelect
				{form}
				multiple
				options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
				field="reviewers"
				cacheLock={cacheLocks['reviewers']}
				bind:cachedValue={formDataCache['reviewers']}
				label={m.reviewers()}
			/>
			<TextField
				type="date"
				{form}
				field="eta"
				label={m.eta()}
				helpText={m.etaHelpText()}
				cacheLock={cacheLocks['eta']}
				bind:cachedValue={formDataCache['eta']}
			/>
			<TextField
				type="date"
				{form}
				field="due_date"
				label={m.dueDate()}
				helpText={m.dueDateHelpText()}
				cacheLock={cacheLocks['due_date']}
				bind:cachedValue={formDataCache['due_date']}
			/>
		{/if}
	{:else if URLModel === 'threats'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hide={initialData.folder}
		/>
		<TextField
			{form}
			field="ref_id"
			label={m.ref()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<TextArea
			{form}
			field="annotation"
			label={m.annotation()}
			cacheLock={cacheLocks['annotation']}
			bind:cachedValue={formDataCache['annotation']}
		/>
		<TextField
			{form}
			field="provider"
			label={m.provider()}
			cacheLock={cacheLocks['provider']}
			bind:cachedValue={formDataCache['provider']}
		/>
	{:else if URLModel === 'risk-scenarios'}
		<AutocompleteSelect
			{form}
			options={getOptions({
				objects: model.foreignKeys['risk_assessment'],
				label: 'str',
				extra_fields: [['project', 'str']]
			})}
			field="risk_assessment"
			cacheLock={cacheLocks['risk_assessment']}
			bind:cachedValue={formDataCache['risk_assessment']}
			label={m.riskAssessment()}
			hide={initialData.risk_assessment}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({
				objects: model.foreignKeys['threats'],
				extra_fields: [['folder', 'str']],
				label: 'auto' // convention for automatic label calculation
			})}
			field="threats"
			cacheLock={cacheLocks['threats']}
			bind:cachedValue={formDataCache['threats']}
			label={m.threats()}
		/>
	{:else if URLModel === 'applied-controls' || URLModel === 'policies'}
		{#if schema.shape.category}
			<Select
				{form}
				options={model.selectOptions['category']}
				field="category"
				label={m.category()}
				cacheLock={cacheLocks['category']}
				bind:cachedValue={formDataCache['category']}
			/>
		{/if}
		<Select
			{form}
			options={model.selectOptions['csf_function']}
			field="csf_function"
			label={m.csfFunction()}
			cacheLock={cacheLocks['csf_function']}
			bind:cachedValue={formDataCache['csf_function']}
		/>
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			label={m.status()}
			cacheLock={cacheLocks['status']}
			bind:cachedValue={formDataCache['status']}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({
				objects: model.foreignKeys['evidences'],
				extra_fields: [['folder', 'str']]
			})}
			field="evidences"
			cacheLock={cacheLocks['evidences']}
			bind:cachedValue={formDataCache['evidences']}
			label={m.evidences()}
		/>
		<TextField
			type="date"
			{form}
			field="eta"
			label={m.eta()}
			helpText={m.etaHelpText()}
			cacheLock={cacheLocks['eta']}
			bind:cachedValue={formDataCache['eta']}
		/>
		<TextField
			type="date"
			{form}
			field="expiry_date"
			label={m.expiryDate()}
			helpText={m.expiryDateHelpText()}
			cacheLock={cacheLocks['expiry_date']}
			bind:cachedValue={formDataCache['expiry_date']}
		/>
		<TextField
			{form}
			field="link"
			label={m.link()}
			helpText={m.linkHelpText()}
			cacheLock={cacheLocks['link']}
			bind:cachedValue={formDataCache['link']}
		/>
		<Select
			{form}
			options={model.selectOptions['effort']}
			field="effort"
			label={m.effort()}
			helpText={m.effortHelpText()}
			cacheLock={cacheLocks['effort']}
			bind:cachedValue={formDataCache['effort']}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hide={initialData.folder}
		/>
	{:else if URLModel === 'risk-acceptances'}
		<TextField
			{form}
			type="date"
			field="expiry_date"
			label={m.expiryDate()}
			helpText={m.expiryDateHelpText()}
			cacheLock={cacheLocks['expiry_date']}
			bind:cachedValue={formDataCache['expiry_date']}
		/>
		{#if object.id && $page.data.user.id === object.approver}
			<TextArea
				disabled={$page.data.user.id !== object.approver}
				{form}
				field="justification"
				label={m.justification()}
				helpText={m.riskAcceptanceJusitficationHelpText()}
				cacheLock={cacheLocks['justification']}
				bind:cachedValue={formDataCache['justification']}
			/>
		{/if}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hide={initialData.folder}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['approver'], label: 'email' })}
			field="approver"
			cacheLock={cacheLocks['approver']}
			bind:cachedValue={formDataCache['approver']}
			label={m.approver()}
			helpText={m.approverHelpText()}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({
				objects: model.foreignKeys['risk_scenarios'],
				extra_fields: [
					['project', 'str'],
					['risk_assessment', 'str']
				]
			})}
			field="risk_scenarios"
			cacheLock={cacheLocks['risk_scenarios']}
			bind:cachedValue={formDataCache['risk_scenarios']}
			label={m.riskScenarios()}
			helpText={m.riskAcceptanceRiskScenariosHelpText()}
			multiple
		/>
	{:else if URLModel === 'reference-controls'}
		<TextField
			{form}
			field="ref_id"
			label={m.ref()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<Select
			{form}
			options={model.selectOptions['category']}
			field="category"
			label={m.category()}
			cacheLock={cacheLocks['category']}
			bind:cachedValue={formDataCache['category']}
		/>
		<Select
			{form}
			options={model.selectOptions['csf_function']}
			field="csf_function"
			label={m.csfFunction()}
			cacheLock={cacheLocks['csf_function']}
			bind:cachedValue={formDataCache['csf_function']}
		/>
		<TextArea
			{form}
			field="annotation"
			label={m.annotation()}
			cacheLock={cacheLocks['annotation']}
			bind:cachedValue={formDataCache['annotation']}
		/>
		<TextField
			{form}
			field="provider"
			label={m.provider()}
			cacheLock={cacheLocks['provider']}
			bind:cachedValue={formDataCache['provider']}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hide={initialData.folder}
		/>
	{:else if URLModel === 'evidences'}
		<HiddenInput {form} field="applied_controls" />
		<HiddenInput {form} field="requirement_assessments" />
		<FileInput
			{form}
			allowPaste={true}
			helpText={object.attachment
				? `${m.attachmentWarningText()}: ${object.attachment}`
				: m.attachmentHelpText()}
			field="attachment"
			label={m.attachment()}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hide={initialData.applied_controls || initialData.requirement_assessments}
		/>
		<TextField
			{form}
			field="link"
			label={m.link()}
			helpText={m.linkHelpText()}
			cacheLock={cacheLocks['link']}
			bind:cachedValue={formDataCache['link']}
		/>
	{:else if URLModel === 'compliance-assessments'}
		<AutocompleteSelect
			{form}
			hide={context !== 'fromBaseline' || initialData.baseline}
			field="baseline"
			cacheLock={cacheLocks['baseline']}
			bind:cachedValue={formDataCache['baseline']}
			label={m.baseline()}
			options={getOptions({ objects: model.foreignKeys['baseline'] })}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({
				objects: model.foreignKeys['project'],
				extra_fields: [['folder', 'str']]
			})}
			field="project"
			cacheLock={cacheLocks['project']}
			bind:cachedValue={formDataCache['project']}
			label={m.project()}
			hide={initialData.project}
		/>
		<TextField
			{form}
			field="version"
			label={m.version()}
			cacheLock={cacheLocks['version']}
			bind:cachedValue={formDataCache['version']}
		/>
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			label={m.status()}
			cacheLock={cacheLocks['status']}
			bind:cachedValue={formDataCache['status']}
		/>
		<AutocompleteSelect
			{form}
			disabled={object.id}
			options={getOptions({ objects: model.foreignKeys['framework'] })}
			field="framework"
			cacheLock={cacheLocks['framework']}
			bind:cachedValue={formDataCache['framework']}
			label={m.framework()}
			on:change={async (e) => {
				if (e.detail) {
					await fetch(`/frameworks/${e.detail}`)
						.then((r) => r.json())
						.then((r) => {
							const implementation_groups = r['implementation_groups_definition'] || [];
							model.selectOptions['selected_implementation_groups'] = implementation_groups.map(
								(group) => ({ label: group.name, value: group.ref_id })
							);
						});
				}
			}}
		/>
		{#if model.selectOptions['selected_implementation_groups'] && model.selectOptions['selected_implementation_groups'].length}
			<AutocompleteSelect
				multiple
				translateOptions={false}
				{form}
				options={model.selectOptions['selected_implementation_groups']}
				field="selected_implementation_groups"
				cacheLock={cacheLocks['selected_implementation_groups']}
				bind:cachedValue={formDataCache['selected_implementation_groups']}
				label={m.selectedImplementationGroups()}
			/>
		{/if}
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
			field="authors"
			cacheLock={cacheLocks['authors']}
			bind:cachedValue={formDataCache['authors']}
			label={m.authors()}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
			field="reviewers"
			cacheLock={cacheLocks['reviewers']}
			bind:cachedValue={formDataCache['reviewers']}
			label={m.reviewers()}
		/>
		<TextField
			type="date"
			{form}
			field="eta"
			label={m.eta()}
			helpText={m.etaHelpText()}
			cacheLock={cacheLocks['eta']}
			bind:cachedValue={formDataCache['eta']}
		/>
		<TextField
			type="date"
			{form}
			field="due_date"
			label={m.dueDate()}
			helpText={m.dueDateHelpText()}
			cacheLock={cacheLocks['due_date']}
			bind:cachedValue={formDataCache['due_date']}
		/>
	{:else if URLModel === 'assets'}
		<TextArea
			{form}
			field="business_value"
			label={m.businessValue()}
			cacheLock={cacheLocks['business_value']}
			bind:cachedValue={formDataCache['business_value']}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hide={initialData.folder}
		/>
		<Select
			{form}
			options={model.selectOptions['type']}
			field="type"
			label="Type"
			cacheLock={cacheLocks['type']}
			bind:cachedValue={formDataCache['type']}
		/>
		<AutocompleteSelect
			disabled={data.type === 'PR'}
			multiple
			{form}
			options={getOptions({ objects: model.foreignKeys['parent_assets'], self: object })}
			field="parent_assets"
			cacheLock={cacheLocks['parent_assets']}
			bind:cachedValue={formDataCache['parent_assets']}
			label={m.parentAssets()}
		/>
	{:else if URLModel === 'requirement-assessments'}
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			label={m.status()}
			cacheLock={cacheLocks['status']}
			bind:cachedValue={formDataCache['status']}
		/>
		<Select
			{form}
			options={model.selectOptions['result']}
			field="result"
			label={m.result()}
			cacheLock={cacheLocks['result']}
			bind:cachedValue={formDataCache['result']}
		/>
		<TextArea
			{form}
			field="observation"
			label={m.observation()}
			cacheLock={cacheLocks['observation']}
			bind:cachedValue={formDataCache['observation']}
		/>
		<HiddenInput {form} field="folder" />
		<HiddenInput {form} field="requirement" />
		<HiddenInput {form} field="compliance_assessment" />
	{:else if URLModel === 'entities'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['owned_folders'] })}
			field="owned_folders"
			multiple
			cacheLock={cacheLocks['owned_folders']}
			bind:cachedValue={formDataCache['owned_folders']}
			label={m.ownedFolders()}
			hide={initialData.owned_folders}
		/>
		<TextArea
			{form}
			field="mission"
			label={m.mission()}
			cacheLock={cacheLocks['mission']}
			bind:cachedValue={formDataCache['mission']}
		/>
		<TextField
			{form}
			field="reference_link"
			label={m.referenceLink()}
			helpText={m.linkHelpText()}
			cacheLock={cacheLocks['reference_link']}
			bind:cachedValue={formDataCache['reference_link']}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			label={m.domain()}
			hide={initialData.folder}
		/>
	{:else if URLModel === 'entity-assessments'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['entity'] })}
			field="entity"
			cacheLock={cacheLocks['entity']}
			bind:cachedValue={formDataCache['entity']}
			label={m.entity()}
			hide={initialData.entity}
		/>
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			label={m.status()}
			cacheLock={cacheLocks['status']}
			bind:cachedValue={formDataCache['status']}
		/>
		<TextField
			{form}
			field="reference_link"
			label={m.referenceLink()}
			helpText={m.linkHelpText()}
			cacheLock={cacheLocks['reference_link']}
			bind:cachedValue={formDataCache['reference_link']}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['project'] })}
			field="project"
			cacheLock={cacheLocks['project']}
			bind:cachedValue={formDataCache['project']}
			label={m.project()}
			hide={initialData.project}
		/>
		<TextField
			{form}
			field="version"
			label={m.version()}
			cacheLock={cacheLocks['version']}
			bind:cachedValue={formDataCache['version']}
		/>
		<TextField
			type="date"
			{form}
			field="eta"
			label={m.eta()}
			helpText={m.etaHelpText()}
			cacheLock={cacheLocks['eta']}
			bind:cachedValue={formDataCache['eta']}
		/>
		<TextField
			type="date"
			{form}
			field="due_date"
			label={m.dueDate()}
			helpText={m.dueDateHelpText()}
			cacheLock={cacheLocks['due_date']}
			bind:cachedValue={formDataCache['due_date']}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
			field="authors"
			cacheLock={cacheLocks['authors']}
			bind:cachedValue={formDataCache['authors']}
			label={m.authors()}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
			field="reviewers"
			cacheLock={cacheLocks['reviewers']}
			bind:cachedValue={formDataCache['reviewers']}
			label={m.reviewers()}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['compliance_assessment'], label: 'str' })}
			field="compliance_assessment"
			cacheLock={cacheLocks['compliance_assessment']}
			bind:cachedValue={formDataCache['compliance_assessment']}
			label={m.complianceAssessment()}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({
				objects: model.foreignKeys['evidence'],
				extra_fields: [['folder', 'str']]
			})}
			field="evidence"
			cacheLock={cacheLocks['evidence']}
			bind:cachedValue={formDataCache['evidence']}
			label={m.evidence()}
		/>
		<Score {form} label={m.criticality()} field="criticality" always_enabled={true} max_score={5} />
		<Score {form} label={m.penetration()} field="penetration" always_enabled={true} max_score={5} />
		<Score {form} label={m.dependency()} field="dependency" always_enabled={true} max_score={5} />
		<Score {form} label={m.maturity()} field="maturity" always_enabled={true} max_score={5} />
		<Score {form} label={m.trust()} field="trust" always_enabled={true} max_score={5} />
	{:else if URLModel === 'solutions'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['provider_entity'] })}
			field="provider_entity"
			cacheLock={cacheLocks['provider_entity']}
			bind:cachedValue={formDataCache['provider_entity']}
			label={m.providerEntity()}
			hide={initialData.provider_entity}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['recipient_entity'] })}
			field="recipient_entity"
			cacheLock={cacheLocks['recipient_entity']}
			bind:cachedValue={formDataCache['recipient_entity']}
			label={m.recipientEntity()}
			hide={initialData.recipient_entity}
		/>
		<TextField
			{form}
			field="ref_id"
			label={m.ref()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<Score {form} label={m.criticality()} field="criticality" always_enabled={true} max_score={5} />
	{:else if URLModel === 'products'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['solution'] })}
			field="solution"
			cacheLock={cacheLocks['solution']}
			bind:cachedValue={formDataCache['solution']}
			label={m.solution()}
			hide={initialData.solution}
		/>
	{:else if URLModel === 'representatives'}
		<TextField
			{form}
			field="email"
			label={m.email()}
			cacheLock={cacheLocks['email']}
			bind:cachedValue={formDataCache['email']}
			data-focusindex="2"
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['entity'] })}
			field="entity"
			cacheLock={cacheLocks['entity']}
			bind:cachedValue={formDataCache['entity']}
			label={m.entity()}
		/>
		<TextField
			{form}
			field="first_name"
			label={m.firstName()}
			cacheLock={cacheLocks['first_name']}
			bind:cachedValue={formDataCache['first_name']}
		/>
		<TextField
			{form}
			field="last_name"
			label={m.lastName()}
			cacheLock={cacheLocks['last_name']}
			bind:cachedValue={formDataCache['last_name']}
		/>
		<TextField
			{form}
			field="phone"
			label={m.phone()}
			cacheLock={cacheLocks['phone']}
			bind:cachedValue={formDataCache['phone']}
		/>
		<TextField
			{form}
			field="role"
			label={m.role()}
			cacheLock={cacheLocks['role']}
			bind:cachedValue={formDataCache['role']}
		/>
	{:else if URLModel === 'frameworks'}
		<TextField
			{form}
			field="ref_id"
			label={m.ref()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<Select
			{form}
			options={model.selectOptions['category']}
			field="category"
			label={m.category()}
			cacheLock={cacheLocks['category']}
			bind:cachedValue={formDataCache['category']}
		/>
	{:else if URLModel === 'users'}
		<TextField
			{form}
			field="email"
			label={m.email()}
			cacheLock={cacheLocks['email']}
			bind:cachedValue={formDataCache['email']}
			data-focusindex="2"
		/>
		{#if shape.first_name && shape.last_name}
			<TextField
				{form}
				field="first_name"
				label={m.firstName()}
				cacheLock={cacheLocks['first_name']}
				bind:cachedValue={formDataCache['first_name']}
			/>
			<TextField
				{form}
				field="last_name"
				label={m.lastName()}
				cacheLock={cacheLocks['last_name']}
				bind:cachedValue={formDataCache['last_name']}
			/>
		{/if}
		{#if shape.user_groups}
			<AutocompleteSelect
				{form}
				multiple
				options={getOptions({ objects: model.foreignKeys['user_groups'] })}
				field="user_groups"
				cacheLock={cacheLocks['user_groups']}
				bind:cachedValue={formDataCache['user_groups']}
				label={m.userGroups()}
			/>
		{/if}
		{#if shape.is_active}
			<Checkbox {form} field="is_active" label={m.isActive()} helpText={m.isActiveHelpText()} />
		{/if}
	{:else if URLModel === 'sso-settings'}
		<Accordion>
			<Checkbox {form} field="is_enabled" label={m.enableSSO()} />
			<AutocompleteSelect
				{form}
				hide={model.selectOptions['provider'].length < 2}
				field="provider"
				cacheLock={cacheLocks['provider']}
				bind:cachedValue={formDataCache['provider']}
				options={model.selectOptions['provider']}
				label={m.provider()}
				disabled={!data.is_enabled}
			/>
			{#if data.provider !== 'saml'}
				<AccordionItem open>
					<svelte:fragment slot="summary">{m.IdPConfiguration()}</svelte:fragment>
					<svelte:fragment slot="content">
						<TextField
							{form}
							field="provider_name"
							label={m.name()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['provider_name']}
							bind:cachedValue={formDataCache['provider_name']}
						/>
						<TextField
							hidden
							{form}
							field="provider_id"
							label={m.providerID()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['provider_id']}
							bind:cachedValue={formDataCache['provider_id']}
						/>
						<TextField
							{form}
							field="client_id"
							label={m.clientID()}
							helpText={m.clientIDHelpText()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['client_id']}
							bind:cachedValue={formDataCache['client_id']}
						/>
						{#if data.provider !== 'saml'}
							<TextField
								{form}
								field="secret"
								label={m.secret()}
								helpText={m.secretHelpText()}
								disabled={!data.is_enabled}
								cacheLock={cacheLocks['secret']}
								bind:cachedValue={formDataCache['secret']}
							/>
							<TextField
								{form}
								field="key"
								label={m.key()}
								disabled={!data.is_enabled}
								cacheLock={cacheLocks['key']}
								bind:cachedValue={formDataCache['key']}
							/>
						{/if}
					</svelte:fragment>
				</AccordionItem>
			{/if}
			{#if data.provider === 'saml'}
				<AccordionItem open>
					<svelte:fragment slot="summary"
						><span class="font-semibold">{m.SAMLIdPConfiguration()}</span></svelte:fragment
					>
					<svelte:fragment slot="content">
						<TextField
							{form}
							field="idp_entity_id"
							label={m.IdPEntityID()}
							required={data.provider === 'saml'}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['idp_entity_id']}
							bind:cachedValue={formDataCache['idp_entity_id']}
						/>
						<TextField
							{form}
							field="metadata_url"
							label={m.metadataURL()}
							required={data.provider === 'saml'}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['metadata_url']}
							bind:cachedValue={formDataCache['metadata_url']}
						/>
						<TextField
							hidden
							{form}
							field="sso_url"
							label={m.SSOURL()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['sso_url']}
							bind:cachedValue={formDataCache['sso_url']}
						/>
						<TextField
							hidden
							{form}
							field="slo_url"
							label={m.SLOURL()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['slo_url']}
							bind:cachedValue={formDataCache['slo_url']}
						/>
						<TextArea
							hidden
							{form}
							field="x509cert"
							label={m.x509Cert()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['x509cert']}
							bind:cachedValue={formDataCache['x509cert']}
						/>
					</svelte:fragment>
				</AccordionItem>

				<AccordionItem>
					<svelte:fragment slot="summary"
						><span class="font-semibold">{m.SPConfiguration()}</span></svelte:fragment
					>
					<svelte:fragment slot="content">
						<TextField
							{form}
							field="sp_entity_id"
							label={m.SPEntityID()}
							required={data.provider === 'saml'}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['sp_entity_id']}
							bind:cachedValue={formDataCache['sp_entity_id']}
						/>
					</svelte:fragment>
				</AccordionItem>

				<AccordionItem
					><svelte:fragment slot="summary"
						><span class="font-semibold">{m.advancedSettings()}</span></svelte:fragment
					>
					<svelte:fragment slot="content">
						<TextField
							{form}
							field="attribute_mapping_uid"
							label={m.attributeMappingUID()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['attribute_mapping_uid']}
							bind:cachedValue={formDataCache['attribute_mapping_uid']}
						/>
						<TextField
							{form}
							field="attribute_mapping_email_verified"
							label={m.attributeMappingEmailVerified()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['attribute_mapping_email_verified']}
							bind:cachedValue={formDataCache['attribute_mapping_email_verified']}
						/>
						<TextField
							{form}
							field="attribute_mapping_email"
							label={m.attributeMappingEmail()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['attribute_mapping_email']}
							bind:cachedValue={formDataCache['attribute_mapping_email']}
						/>

						<Checkbox
							{form}
							field="allow_repeat_attribute_name"
							label={m.allowRepeatAttributeName()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="allow_single_label_domains"
							label={m.allowSingleLabelDomains()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="authn_request_signed"
							hidden
							label={m.authnRequestSigned()}
							disabled={!data.is_enabled}
						/>
						<TextField
							{form}
							field="digest_algorithm"
							hidden
							label={m.digestAlgorithm()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['digest_algorithm']}
							bind:cachedValue={formDataCache['digest_algorithm']}
						/>
						<Checkbox
							{form}
							field="logout_request_signed"
							hidden
							label={m.logoutRequestSigned()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="logout_response_signed"
							hidden
							label={m.logoutResponseSigned()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="metadata_signed"
							hidden
							label={m.metadataSigned()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="name_id_encrypted"
							hidden
							label={m.nameIDEncrypted()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							hidden
							field="reject_deprecated_algorithm"
							label={m.rejectDeprecatedAlgorithm()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="reject_idp_initiated_sso"
							label={m.rejectIdPInitiatedSSO()}
							disabled={!data.is_enabled}
						/>
						<TextField
							{form}
							field="signature_algorithm"
							hidden
							label={m.signatureAlgorithm()}
							disabled={!data.is_enabled}
							cacheLock={cacheLocks['signature_algorithm']}
							bind:cachedValue={formDataCache['signature_algorithm']}
						/>
						<Checkbox
							{form}
							field="want_assertion_encrypted"
							hidden
							label={m.wantAssertionEncrypted()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="want_assertion_signed"
							hidden
							label={m.wantAssertionSigned()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="want_attribute_statement"
							label={m.wantAttributeStatement()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="want_message_signed"
							hidden
							label={m.wantMessageSigned()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="want_name_id"
							label={m.wantNameID()}
							disabled={!data.is_enabled}
						/>
						<Checkbox
							{form}
							field="want_name_id_encrypted"
							hidden
							label={m.wantNameIDEncrypted()}
							disabled={!data.is_enabled}
						/>
					</svelte:fragment>
				</AccordionItem>
			{/if}
		</Accordion>
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
