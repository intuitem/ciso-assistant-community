<!-- @migration-task Error while migrating Svelte code: $$props is used together with named props in a way that cannot be automatically migrated. -->
<script lang="ts">
	// Props
	/** Exposes parent props to this component. */
	export let parent: any;

	// Stores
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { goto } from '$lib/utils/breadcrumbs';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import { defaults, superForm, type SuperValidated } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';

	import * as m from '$paraglide/messages';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import { quickStartSchema } from '$lib/utils/schemas';
	import { getLocale } from '$paraglide/runtime';

	const modalStore: ModalStore = getModalStore();

	export let invalidateAll = true; // set to false to keep form data using muliple forms on a page
	export let formAction = '/quick-start?/create';
	export let additionalInitialData = {};
	export let suggestions: { [key: string]: any } = {};

	export let debug = false;

	let closeModal = true;

	// Base Classes
	const cBase = 'card p-4 w-fit max-w-4xl shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	const form = defaults(
		{
			framework: 'urn:intuitem:risk:library:iso27001-2022',
			risk_matrix: 'urn:intuitem:risk:library:critical_risk_matrix_5x5',
			audit_name: `Quick start audit ${new Date().toLocaleTimeString(getLocale(), { hour: '2-digit', minute: '2-digit' })}`,
			risk_assessment_name: `Quick start risk assessment ${new Date().toLocaleTimeString(getLocale(), { hour: '2-digit', minute: '2-digit' })}`
		},
		zod(quickStartSchema)
	);

	const _form = superForm(form, {
		dataType: 'json',
		invalidateAll,
		applyAction: $$props.applyAction ?? true,
		resetForm: $$props.resetForm ?? false,
		validators: zod(quickStartSchema),
		taintedMessage: m.taintedFormMessage(),
		validationMethod: 'auto',
		onUpdated: async ({ form }) => {
			if (form.message?.redirect) {
				goto(getSecureRedirect(form.message.redirect));
			}
			if (form.valid) {
				parent.onConfirm();
			}
		}
	});
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<div class="flex items-center justify-between">
			<header class={cHeader} data-testid="modal-title">
				{$modalStore[0].title ?? '(title missing)'}
			</header>
			<div
				role="button"
				tabindex="0"
				class="flex items-center hover:text-primary-500 cursor-pointer"
				on:click={parent.onClose}
				on:keydown={parent.onClose}
			>
				<i class="fa-solid fa-xmark" />
			</div>
		</div>
		<SuperForm
			class="flex flex-col space-y-3"
			dataType="json"
			enctype="application/x-www-form-urlencoded"
			data={form}
			{_form}
			{invalidateAll}
			let:form
			let:data
			let:initialData
			validators={zod(quickStartSchema)}
			action={formAction}
			{...$$restProps}
		>
			<AutocompleteSelect
				{form}
				field="framework"
				label={m.framework()}
				optionsEndpoint="stored-libraries"
				optionsDetailedUrlParameters={[['object_type', 'framework']]}
				optionsValueField="urn"
			/>
			<TextField {form} field="audit_name" label={m.auditName()} />
			<Checkbox {form} field="create_risk_assessment" label={m.createRiskAssessment()} />
			<TextField
				{form}
				field="risk_assessment_name"
				label={m.riskAssessmentName()}
				disabled={!data.create_risk_assessment}
			/>
			<AutocompleteSelect
				{form}
				field="risk_matrix"
				label={m.riskMatrix()}
				optionsEndpoint="stored-libraries"
				optionsDetailedUrlParameters={[['object_type', 'risk_matrix']]}
				optionsValueField="urn"
				disabled={!data.create_risk_assessment}
			/>
			<div class="flex flex-row justify-between space-x-4">
				<button
					class="btn bg-gray-400 text-white font-semibold w-full"
					data-testid="cancel-button"
					type="button"
					on:click={(event) => {
						parent.onClose(event);
					}}>{m.cancel()}</button
				>

				<button
					class="btn variant-filled-primary font-semibold w-full"
					data-testid="save-button"
					type="submit">{m.save()}</button
				>
			</div>
		</SuperForm>
	</div>
{/if}
