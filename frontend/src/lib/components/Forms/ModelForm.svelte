<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';

	import AutocompleteSelect from './AutocompleteSelect.svelte';
	import Select from './Select.svelte';

	import { getOptions } from '$lib/utils/crud';
	import { modelSchema } from '$lib/utils/schemas';
	import type { ModelInfo, urlModel } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import HiddenInput from './HiddenInput.svelte';
	import FileInput from './FileInput.svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages.js';
	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let form: SuperValidated<AnyZodObject>;
	export let model: ModelInfo;
	export let origin: string = "default";
	export let closeModal = false;
	export let parent: any;
	export let suggestions: { [key: string]: any } = {};

	const URLModel = model.urlModel as urlModel;
	export let schema = modelSchema(URLModel);
	export let object: Record<string, any> = {};

	function cancel(): void {
		if (browser) {
			var currentUrl = window.location.href;
			var url = new URL(currentUrl);
			var nextValue = url.searchParams.get('next');
			if (nextValue) window.location.href = nextValue;
		}
	}
	$: shape = schema.shape || schema._def.schema.shape;
	let updated_fields = new Set();
</script>

<SuperForm
	class="flex flex-col space-y-3"
	dataType={shape.attachment ? 'form' : 'json'}
	enctype={shape.attachment ? 'multipart/form-data' : 'application/x-www-form-urlencoded'}
	data={form}
	let:form
	let:data
	let:initialData
	validators={schema}
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
				suggestions: suggestions['reference_control']
			})}
			field="reference_control"
			label={m.referenceControl()}
			on:change={async (e) => {
				if (e.detail) {
					await fetch(`/reference-controls/${e.detail}`)
						.then((r) => r.json())
						.then((r) => {
							form.form.update((currentData) => {
								if (
									origin === "edit" &&
									currentData['reference_control'] === initialData['reference_control'] &&
									!updated_fields.has('reference_control')
								) {
									return currentData; // Keep the current values in the edit form.
								}
								updated_fields.add('reference_control');
								return { ...currentData, category: r.category };
							});
						});
				}
			}}
		/>
	{/if}
	{#if shape.name}
		<TextField {form} field="name" label={m.name()} />
	{/if}
	{#if shape.description}
		<TextArea {form} field="description" label={m.description()} />
	{/if}
	{#if URLModel === 'projects'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label={m.domain()}
			hide={initialData.folder}
		/>
		<TextField {form} field="internal_reference" label={m.internalReference()} />
		<AutocompleteSelect
			{form}
			options={model.selectOptions['lc_status']}
			field="lc_status"
			label={m.lcStatus()}
		/>
	{:else if URLModel === 'risk-assessments'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['project'] })}
			field="project"
			label={m.project()}
			hide={initialData.project}
		/>
		<TextField {form} field="version" label={m.version()} />
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			label={m.status()}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['risk_matrix'] })}
			field="risk_matrix"
			label={m.riskMatrix()}
			helpText={m.riskAssessmentMatrixHelpText()}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
			field="authors"
			label={m.authors()}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
			field="reviewers"
			label={m.reviewers()}
		/>
		<TextField
			type="date"
			{form}
			field="eta"
			label={m.eta()}
			helpText={m.etaHelpText()}
		/>
		<TextField
			type="date"
			{form}
			field="due_date"
			label={m.dueDate()}
			helpText={m.dueDateHelpText()}
		/>
	{:else if URLModel === 'threats'}
		<TextField {form} field="ref_id" label={m.ref()} />
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label={m.domain()}
			hide={initialData.folder}
		/>
		<TextField {form} field="provider" label={m.provider()} />
	{:else if URLModel === 'risk-scenarios'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['risk_assessment'] })}
			field="risk_assessment"
			label={m.riskAssessment()}
			hide={initialData.risk_assessment}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['threats'] })}
			field="threats"
			label={m.threats()}
		/>
	{:else if URLModel === 'applied-controls' || URLModel === 'policies'}
		{#if schema.shape.category}
			<Select
				{form}
				options={model.selectOptions['category']}
				field="category"
				label={m.category()}
			/>
		{/if}
		<Select {form} options={model.selectOptions['status']} field="status" label={m.status()} />
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['evidences'] })}
			field="evidences"
			label={m.evidences()}
		/>
		<TextField
			type="date"
			{form}
			field="eta"
			label={m.eta()}
			helpText={m.etaHelpText()}
		/>
		<TextField
			type="date"
			{form}
			field="expiry_date"
			label={m.expiryDate()}
			helpText={m.expiryDateHelpText()}
		/>
		<TextField
			{form}
			field="link"
			label={m.link()}
			helpText={m.linkHelpText()}
		/>
		<Select
			{form}
			options={model.selectOptions['effort']}
			field="effort"
			label={m.effort()}
			helpText={m.effortHelpText()}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
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
		/>
		{#if object.id && $page.data.user.id === object.approver}
			<TextArea
				disabled={$page.data.user.id !== object.approver}
				{form}
				field="justification"
				label={m.justification()}
				helpText={m.riskAcceptanceJusitficationHelpText()}
			/>
		{/if}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label={m.domain()}
			hide={initialData.folder}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['approver'], label: 'email' })}
			field="approver"
			label={m.approver()}
			helpText={m.approverHelpText()}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['risk_scenarios'] })}
			field="risk_scenarios"
			label={m.riskScenarios()}
			helpText={m.riskAcceptanceRiskScenariosHelpText()}
			multiple
		/>
	{:else if URLModel === 'reference-controls'}
		<TextField {form} field="ref_id" label={m.ref()} />
		<Select
			{form}
			options={model.selectOptions['category']}
			field="category"
			label={m.category()}
		/>
		<TextField {form} field="provider" label={m.provider()} />
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label={m.domain()}
			hide={initialData.folder}
		/>
	{:else if URLModel === 'evidences'}
		<FileInput
			{form}
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
			label={m.domain()}
			hide={initialData.applied_controls || initialData.requirement_assessments}
		/>
		<TextField
			{form}
			field="link"
			label={m.link()}
			helpText={m.linkHelpText()}
		/>
	{:else if URLModel === 'compliance-assessments'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['project'] })}
			field="project"
			label={m.project()}
			hide={initialData.project}
		/>
		<TextField {form} field="version" label={m.version()} />
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			label={m.status()}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['framework'] })}
			field="framework"
			label={m.framework()}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
			field="authors"
			label={m.authors()}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
			field="reviewers"
			label={m.reviewers()}
		/>
		<TextField
			type="date"
			{form}
			field="eta"
			label={m.eta()}
			helpText={m.etaHelpText()}
		/>
		<TextField
			type="date"
			{form}
			field="due_date"
			label={m.dueDate()}
			helpText={m.dueDateHelpText()}
		/>
	{:else if URLModel === 'assets'}
		<TextArea {form} field="business_value" label={m.businessValue()} />
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label={m.domain()}
			hide={initialData.folder}
		/>
		<Select {form} options={model.selectOptions['type']} field="type" label="Type" />
		<AutocompleteSelect
			disabled={data.type === 'PR'}
			multiple
			{form}
			options={getOptions({ objects: model.foreignKeys['parent_assets'], self: object })}
			field="parent_assets"
			label={m.parentAssets()}
		/>
	{:else if URLModel === 'requirement-assessments'}
		<Select {form} options={model.selectOptions['status']} field="status" label={m.status()} />
		<TextArea {form} field="observation" label={m.observation()} />
		<HiddenInput {form} field="folder" />
		<HiddenInput {form} field="requirement" />
		<HiddenInput {form} field="compliance_assessment" />
	{:else if URLModel === 'users'}
		<TextField {form} field="email" label={m.email()} />
		{#if shape.first_name && shape.last_name}
			<TextField {form} field="first_name" label={m.firstName()} />
			<TextField {form} field="last_name" label={m.lastName()} />
		{/if}
		{#if shape.user_groups}
			<AutocompleteSelect
				{form}
				multiple
				options={getOptions({ objects: model.foreignKeys['user_groups'] })}
				field="user_groups"
				label={m.userGroups()}
			/>
		{/if}
		{#if shape.is_active}
			<Checkbox
				{form}
				field="is_active"
				label={m.isActive()}
				helpText={m.isActiveHelpText()}
			/>
		{/if}
	{/if}
	<div class="flex flex-row justify-between space-x-4">
		{#if closeModal}
			<button
				class="btn bg-gray-400 text-white font-semibold w-full"
				data-testid="cancel-button"
				type="button"
				on:click={parent.onClose}>{m.cancel()}</button
			>
			<button
				class="btn variant-filled-primary font-semibold w-full"
				data-testid="save-button"
				type="submit">{m.save()}</button
			>
		{:else}
			<button
				class="btn bg-gray-400 text-white font-semibold w-full"
				data-testid="cancel-button"
				type="button"
				on:click={cancel}>{m.cancel()}</button
			>
			<button
				class="btn variant-filled-primary font-semibold w-full"
				data-testid="save-button"
				type="submit">{m.save()}</button
			>
		{/if}
	</div>
</SuperForm>
