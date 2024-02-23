<script lang="ts">
	import { RequirementAssessmentSchema } from '$lib/utils/schemas';
	import type { PageData } from './$types';

	export let data: PageData;
	const threats = data.requirement.threats;
	const security_functions = data.requirement.security_functions;

	import { page } from '$app/stores';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import HiddenInput from '$lib/components/Forms/HiddenInput.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { getOptions } from '$lib/utils/crud';
	import { breadcrumbObject } from '$lib/utils/stores';
	import {
		getModalStore,
		getToastStore,
		Tab,
		type ModalComponent,
		type ModalSettings,
		type ModalStore,
		type ToastStore,
		TabGroup
	} from '@skeletonlabs/skeleton';
	import { superForm } from 'sveltekit-superforms/client';

	import * as m from '$paraglide/messages';
	import { localItems, capitalizeFirstLetter } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	function cancel(): void {
		var currentUrl = window.location.href;
		var url = new URL(currentUrl);
		var nextValue = url.searchParams.get('next');
		if (nextValue) window.location.href = nextValue;
	}

	const title =
		(data.parent.display_short ? data.parent.display_short + ': ' : '') +
		data.requirement.display_short;
	breadcrumbObject.set({
		id: data.requirementAssessment.id,
		name: title ?? 'Requirement assessment',
		email: ''
	});

	const schema = RequirementAssessmentSchema;

	const modalStore: ModalStore = getModalStore();
	const toastStore: ToastStore = getToastStore();

	function modalMeasureCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.measureCreateForm,
				formAction: 'createSecurityMeasure',
				model: data.measureModel,
				debug: false,
				suggestions: { security_function: security_functions }
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: localItems(languageTag())['add' + capitalizeFirstLetter(data.measureModel.localName)]
		};
		modalStore.trigger(modal);
	}

	function modalEvidenceCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.evidenceCreateForm,
				formAction: 'createEvidence',
				model: data.evidenceModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: localItems(languageTag())['add' + capitalizeFirstLetter(data.evidenceModel.localName)]
		};
		modalStore.trigger(modal);
	}

	function handleFormUpdated({
		form,
		pageStatus,
		closeModal
	}: {
		form: any;
		pageStatus: number;
		closeModal: boolean;
	}) {
		if (closeModal && form.valid) {
			$modalStore[0] ? modalStore.close() : null;
		}
		if (form.message) {
			const toast: { message: string; background: string } = {
				message: form.message,
				background: pageStatus === 200 ? 'variant-filled-success' : 'variant-filled-error'
			};
			toastStore.trigger(toast);
		}
	}

	let { form: measureCreateForm, message: measureCreateMessage } = {
		form: {},
		message: {}
	};
	let { form: evidenceCreateForm, message: evidenceCreateMessage } = {
		form: {},
		message: {}
	};

	// NOTE: This is a workaround for an issue we had with getting the return value from the form actions after switching pages in route /[model=urlmodel]/ without a full page reload.
	// invalidateAll() did not work.
	$: {
		({ form: measureCreateForm, message: measureCreateMessage } = superForm(
			data.measureCreateForm,
			{
				onUpdated: ({ form }) =>
					handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
			}
		));
		({ form: evidenceCreateForm, message: evidenceCreateMessage } = superForm(
			data.evidenceCreateForm,
			{
				onUpdated: ({ form }) =>
					handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
			}
		));
	}

	let tabSet = 0;
</script>

<div class="card space-y-2 p-4 bg-white shadow">
	<h3 class="h3 font-semibold whitespace-pre-line">
		{title}
	</h3>
	<code class="code">{data.requirement.urn}</code>
	{#if data.requirement.description}
		<p class="whitespace-pre-line">{data.requirement.description}</p>
	{/if}
	{#if (threats && threats.length > 0) || (security_functions && security_functions.length > 0)}
		<div class="card p-4 variant-glass-primary text-sm flex flex-row cursor-auto">
			<div class="flex-1">
				<p class="font-medium">
					<i class="fa-solid fa-gears" />
					Suggested security functions
				</p>
				{#if security_functions.length === 0}
					<p>--</p>
				{:else}
					<ul class="list-disc ml-4">
						{#each security_functions as func}
							<li>
								{#if func.id}
									<a class="anchor" href="/security-functions/{func.id}">
										{func.str}
									</a>
								{:else}
									<p>{func.str}</p>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</div>
			<div class="flex-1">
				<p class="font-medium">
					<i class="fa-solid fa-gears" />
					Threats covered
				</p>
				{#if threats.length === 0}
					<p>--</p>
				{:else}
					<ul class="list-disc ml-4">
						{#each threats as threat}
							<li>
								{#if threat.id}
									<a class="anchor" href="/threats/{threat.id}">
										{threat.str}
									</a>
								{:else}
									<p>{threat.str}</p>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>
	{/if}
	<div class="mt-4">
		<SuperForm
			class="flex flex-col"
			data={data.form}
			dataType="json"
			let:form
			validators={schema}
			action="?/updateRequirementAssessment"
			{...$$restProps}
		>
			<div class="card shadow-lg bg-white">
				<TabGroup>
					<Tab bind:group={tabSet} name="compliance_assessments_tab" value={0}
						>Security measures
					</Tab>
					<Tab bind:group={tabSet} name="risk_assessments_tab" value={1}>Evidences</Tab>
					<svelte:fragment slot="panel">
						{#if tabSet === 0}
							<div
								class="h-full flex flex-col space-y-2 variant-outline-surface rounded-container-token p-4"
							>
								<span class="flex flex-row justify-end items-center">
									<button
										class="btn variant-filled-primary self-end"
										on:click={modalMeasureCreateForm}
										type="button"><i class="fa-solid fa-plus mr-2" />New security measure</button
									>
								</span>
								<AutocompleteSelect
									multiple
									{form}
									options={getOptions({ objects: data.model.foreignKeys['security_measures'] })}
									field="security_measures"
								/>
								<ModelTable
									source={data.tables['security-measures']}
									URLModel="security-measures"
								/>
							</div>
						{/if}
						{#if tabSet === 1}
							<div
								class="h-full flex flex-col space-y-2 variant-outline-surface rounded-container-token p-4"
							>
								<span class="flex flex-row justify-end items-center">
									<button
										class="btn variant-filled-primary self-end"
										on:click={modalEvidenceCreateForm}
										type="button"><i class="fa-solid fa-plus mr-2" />New evidence</button
									>
								</span>
								<AutocompleteSelect
									multiple
									{form}
									options={getOptions({ objects: data.model.foreignKeys['evidences'] })}
									field="evidences"
								/>
								<ModelTable source={data.tables['evidences']} URLModel="evidences" />
							</div>
						{/if}
					</svelte:fragment>
				</TabGroup>
			</div>
			<HiddenInput {form} field="folder" />
			<HiddenInput {form} field="requirement" />
			<HiddenInput {form} field="compliance_assessment" />
			<div class="flex flex-col space-y-3 mt-3">
				<Select {form} options={data.model.selectOptions['status']} field="status" label="Status" />
				<TextArea {form} field="observation" label="Observation" />

				<div class="flex flex-row justify-between space-x-4">
					<button
						class="btn bg-gray-400 text-white font-semibold w-full"
						type="button"
						on:click={cancel}>Cancel</button
					>
					<button class="btn variant-filled-primary font-semibold w-full" type="submit">Save</button
					>
				</div>
			</div>
		</SuperForm>
	</div>
</div>
