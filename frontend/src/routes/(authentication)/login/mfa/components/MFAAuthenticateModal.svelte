<script lang="ts">
	// Props
	

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton-svelte';
	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();


	import SuperForm from '$lib/components/Forms/Form.svelte';

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container';

	import OTPInput from '$lib/components/Forms/OTP/OTPInput.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import { mfaAuthenticateSchema } from '../utils/schemas';
	import TextField from '$lib/components/Forms/TextField.svelte';
	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		_form: any;
		formAction: string;
	}

	let { parent, _form, formAction }: Props = $props();

	let useRecoveryCode = $state(false);
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
