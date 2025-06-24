<script lang="ts">
	import OTPInput from '$lib/components/Forms/OTP/OTPInput.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import { mfaAuthenticateSchema } from '../utils/schemas';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { m } from '$paraglide/messages';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { superForm } from 'sveltekit-superforms';

	const modalStore: ModalStore = getModalStore();

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container';

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		_form: any;
		formAction: string;
	}

	let { parent, _form, formAction }: Props = $props();

	let useRecoveryCode = $state(false);

	const form = superForm(_form, {
		dataType: 'json',
		validators: zod(mfaAuthenticateSchema),
		validationMethod: 'onsubmit',
		onUpdated: async ({ form }) => {
			if (form.valid && parent && typeof parent.onConfirm === 'function') {
				parent.onConfirm();
			}
		}
	});
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>
		<article class="flex flex-col space-y-4 items-center">
			<!-- Enable for debugging: -->
			<SuperForm
				dataType="json"
				action={formAction}
				data={_form}
				_form={form}
				validators={zod(mfaAuthenticateSchema)}
				class="modal-form {cForm}"
				validationMethod="onsubmit"
			>
				{#snippet children({ form })}
					<!-- prettier-ignore -->
					{#if !useRecoveryCode}
					<OTPInput {form} field="code" />
	          {:else}
	        <TextField {form} field="code" label={m.recoveryCode()} />
	        {/if}
					<footer class="modal-footer {parent.regionFooter}">
						<button
							type="button"
							onclick={() => (useRecoveryCode = !useRecoveryCode)}
							class="btn hover:underline"
							data-testid="mfa-authenticate-confirm-button"
						>
							{#if !useRecoveryCode}
								{m.loginUsingRecoveryCode()}
							{:else}
								{m.loginUsingTOTP()}
							{/if}
						</button>
						<button
							class="btn preset-filled-primary-500"
							data-testid="mfa-authenticate-confirm-button"
							type="submit">{m.login()}</button
						>
					</footer>
				{/snippet}
			</SuperForm>
		</article>
	</div>
{/if}
