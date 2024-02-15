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

	export let form: SuperValidated<AnyZodObject>;
	export let model: ModelInfo;
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
	{#if shape.security_function}
		<AutocompleteSelect
			{form}
			options={getOptions({
				objects: model.foreignKeys['security_function'],
				suggestions: suggestions['security_function']
			})}
			field="security_function"
			label="Security function"
			on:change={async (e) => {
				if (e.detail) {
					await fetch(`/security-functions/${e.detail}`)
						.then((r) => r.json())
						.then((r) => {
							form.form.update((currentData) => {
								return { ...currentData, category: r.category };
							});
						});
				}
			}}
		/>
	{/if}
	{#if shape.name}
		<TextField {form} field="name" label="Name" />
	{/if}
	{#if shape.description}
		<TextArea {form} field="description" label="Description" />
	{/if}
	{#if URLModel === 'projects'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label="Domain"
			hide={initialData.folder}
		/>
		<TextField {form} field="internal_reference" label="Internal reference" />
		<AutocompleteSelect
			{form}
			options={model.selectOptions['lc_status']}
			field="lc_status"
			label="Status"
		/>
	{:else if URLModel === 'risk-assessments'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['project'] })}
			field="project"
			label="Project"
			hide={initialData.project}
		/>
		<TextField {form} field="version" label="Version" />
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['risk_matrix'] })}
			field="risk_matrix"
			label="Risk matrix"
			helpText="WARNING: You will not be able to change the risk matrix after the risk assessment is created"
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
			field="authors"
			label="Authors"
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
			field="reviewers"
			label="Reviewers"
		/>
		<TextField type="date" {form} field="eta" label="ETA" helpText="Estimated time of arrival" />
		<TextField
			type="date"
			{form}
			field="due_date"
			label="Due date"
			helpText="Date by which the assessment must be completed"
		/>
	{:else if URLModel === 'threats'}
		<TextField {form} field="ref_id" label="Ref" />
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label="Domain"
			hide={initialData.folder}
		/>
		<TextField {form} field="provider" label="Provider" />
	{:else if URLModel === 'risk-scenarios'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['risk_assessment'] })}
			field="risk_assessment"
			label="RiskAssessment"
			hide={initialData.risk_assessment}
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['threats'] })}
			field="threats"
			label="Threats"
		/>
	{:else if URLModel === 'security-measures' || URLModel === 'policies'}
		{#if schema.shape.category}
			<Select {form} options={model.selectOptions['category']} field="category" label="Category" />
		{/if}
		<Select {form} options={model.selectOptions['status']} field="status" label="Status" />
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['evidences'] })}
			field="evidences"
			label="Evidences"
		/>
		<TextField type="date" {form} field="eta" label="ETA" helpText="Estimated time of arrival" />
		<TextField
			type="date"
			{form}
			field="expiry_date"
			label="Expiry date"
			helpText="Date after which the security measure is no longer valid"
		/>
		<TextField
			{form}
			field="link"
			label="Link"
			helpText="External URL for action follow-up (eg. Jira ticket)"
		/>
		<Select
			{form}
			options={model.selectOptions['effort']}
			field="effort"
			label="Effort"
			helpText="Relative effort of the measure (using T-Shirt sizing)"
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label="Domain"
			hide={initialData.folder}
		/>
	{:else if URLModel === 'risk-acceptances'}
		<TextField
			{form}
			type="date"
			field="expiry_date"
			label="Expiry date"
			helpText="Date after which the risk acceptance will no longer apply"
		/>
		{#if object.id && $page.data.user.id === object.approver}
			<TextArea
				disabled={$page.data.user.id !== object.approver}
				{form}
				field="justification"
				label="Justification"
				helpText="Justification for the risk acceptance. Only the approver can edit this field."
			/>
		{/if}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label="Domain"
			hide={initialData.folder}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['approver'], label: 'email' })}
			field="approver"
			label="Approver"
			helpText="Risk owner and approver identity"
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['risk_scenarios'] })}
			field="risk_scenarios"
			label="Risk scenarios"
			helpText="Risk scenarios to accept"
			multiple
		/>
	{:else if URLModel === 'security-functions'}
		<TextField {form} field="ref_id" label="Ref" />
		<Select {form} options={model.selectOptions['category']} field="category" label="Category" />
		<TextField {form} field="provider" label="Provider" />
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label="Domain"
			hide={initialData.folder}
		/>
	{:else if URLModel === 'evidences'}
		<FileInput
			{form}
			helpText={object.attachment
				? `WARNING: Uploading a new file will overwrite the existing one: ${object.attachment}`
				: 'File for evidence (eg. screenshot, log file, etc.)'}
			field="attachment"
			label="Attachment"
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label="Domain"
			hide={initialData.security_measures || initialData.requirement_assessments}
		/>
		<TextField
			{form}
			field="link"
			label="Link"
			helpText="Link to the evidence (eg. Jira ticket, etc.)"
		/>
	{:else if URLModel === 'compliance-assessments'}
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['project'] })}
			field="project"
			label="Project"
			hide={initialData.project}
		/>
		<TextField {form} field="version" label="Version" />
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['framework'] })}
			field="framework"
			label="Framework"
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
			field="authors"
			label="Authors"
		/>
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
			field="reviewers"
			label="Reviewers"
		/>
		<TextField type="date" {form} field="eta" label="ETA" helpText="Estimated time of arrival" />
		<TextField
			type="date"
			{form}
			field="due_date"
			label="Due date"
			helpText="Date by which the assessment must be completed"
		/>
	{:else if URLModel === 'assets'}
		<TextArea {form} field="business_value" label="Business value" />
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['folder'] })}
			field="folder"
			label="Domain"
			hide={initialData.folder}
		/>
		<Select {form} options={model.selectOptions['type']} field="type" label="Type" />
		<AutocompleteSelect
			disabled={data.type === 'PR'}
			multiple
			{form}
			options={getOptions({ objects: model.foreignKeys['parent_assets'], self: object })}
			field="parent_assets"
			label="Parent assets"
		/>
	{:else if URLModel === 'requirement-assessments'}
		<Select {form} options={model.selectOptions['status']} field="status" label="Status" />
		<TextArea {form} field="observation" label="Observation" />
		<HiddenInput {form} field="folder" />
		<HiddenInput {form} field="requirement" />
		<HiddenInput {form} field="compliance_assessment" />
	{:else if URLModel === 'users'}
		<TextField {form} field="email" label="Email" />
		{#if shape.first_name && shape.last_name}
			<TextField {form} field="first_name" label="First name" />
			<TextField {form} field="last_name" label="Last name" />
		{/if}
		{#if shape.user_groups}
			<AutocompleteSelect
				{form}
				multiple
				options={getOptions({ objects: model.foreignKeys['user_groups'] })}
				field="user_groups"
				label="User Groups"
			/>
		{/if}
		{#if shape.is_active}
			<Checkbox
				{form}
				field="is_active"
				label="Active"
				helpText="Designates whether this user should be treated as active"
			/>
		{/if}
	{/if}
	<div class="flex flex-row justify-between space-x-4">
		{#if closeModal}
			<button
				class="btn bg-gray-400 text-white font-semibold w-full"
				data-testid="cancel-button"
				type="button"
				on:click={parent.onClose}>Cancel</button
			>
			<button
				class="btn variant-filled-primary font-semibold w-full"
				data-testid="save-button"
				type="submit">Save</button
			>
		{:else}
			<button
				class="btn bg-gray-400 text-white font-semibold w-full"
				data-testid="cancel-button"
				type="button"
				on:click={cancel}>Cancel</button
			>
			<button
				class="btn variant-filled-primary font-semibold w-full"
				data-testid="save-button"
				type="submit">Save</button
			>
		{/if}
	</div>
</SuperForm>
