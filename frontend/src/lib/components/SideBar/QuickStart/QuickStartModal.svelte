<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { goto } from '$lib/utils/breadcrumbs';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { defaults, superForm, type SuperValidated } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';

	import * as m from '$paraglide/messages';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import { quickStartSchema } from '$lib/utils/schemas';
	import { getLocale } from '$paraglide/runtime';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		invalidateAll?: boolean; // set to false to keep form data using muliple forms on a page
		formAction?: string;
		additionalInitialData?: any;
		suggestions?: { [key: string]: any };
		debug?: boolean;
		[key: string]: any;
	}

	let {
		parent,
		invalidateAll = true,
		formAction = '/quick-start?/create',
		additionalInitialData = {},
		suggestions = {},
		debug = false,
		...rest
	}: Props = $props();

	let closeModal = true;

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-fit max-w-4xl shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	const form = defaults(
		{
			framework: 'urn:intuitem:risk:library:iso27001-2022',
			risk_matrix: 'urn:intuitem:risk:library:critical_risk_matrix_5x5',
			audit_name: `Quick start audit ${new Date().toLocaleTimeString(getLocale(), { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`,
			risk_assessment_name: `Quick start risk assessment ${new Date().toLocaleTimeString(getLocale(), { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
		},
		zod(quickStartSchema)
	);

	const _form = superForm(form, {
		dataType: 'json',
		invalidateAll,
		applyAction: rest.applyAction ?? true,
		resetForm: rest.resetForm ?? false,
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
				onclick={parent.onClose}
				onkeydown={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</div>
		</div>
		<SuperForm
			class="flex flex-col space-y-3"
			dataType="json"
			enctype="application/x-www-form-urlencoded"
			data={form}
			{_form}
			{invalidateAll}
			validators={zod(quickStartSchema)}
			action={formAction}
			{...rest}
		>
			{#snippet children({ form, data, initialData })}
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
						onclick={(event) => {
							parent.onClose(event);
						}}>{m.cancel()}</button
					>

					<button
						class="btn preset-filled-primary-500 font-semibold w-full"
						data-testid="save-button"
						type="submit">{m.save()}</button
					>
				</div>
			{/snippet}
		</SuperForm>
	</div>
{/if}
