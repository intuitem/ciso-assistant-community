<script lang="ts">
	// Props
	

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();


	import SuperForm from '$lib/components/Forms/Form.svelte';

	// Base Classes
	const cBase = 'card p-4 w-fit shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	import OTPInput from '$lib/components/Forms/OTP/OTPInput.svelte';
	import QR from '@svelte-put/qr/svg/QR.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import { activateTOTPSchema } from '../utils/schemas';
	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		totp: any;
		_form: any;
		formAction: string;
	}

	let {
		parent,
		totp,
		_form,
		formAction
	}: Props = $props();
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article class="flex flex-row space-x-8">
			<div class="flex flex-col space-y-4 items-center">
				<h4 class="h4">{m.step({ number: 1 })}</h4>
				<p class="text-surface-900">{$modalStore[0].body ?? '(body missing)'}</p>
				<QR
					data={totp.totp_url}
					anchorInnerFill="black"
					anchorOuterFill="black"
					width="400"
					height="400"
				/>

				<div class="flex items-center justify-center w-full space-x-2">
					<hr class="w-64 items-center bg-gray-200 border-0" />
					<span class="flex items-center text-gray-600 text-sm">{m.or()}</span>
					<hr class="w-64 items-center bg-gray-200 border-0" />
				</div>

				<div>
					<p class="text-center text-surface-900">{m.enterTOTPCodeManually()}</p>
					<p class="text-center">{totp.secret}</p>
				</div>
			</div>

			<span class="divider-vertical"></span>

			<div class="flex flex-col space-y-4 items-center self-center">
				<h4 class="h4">{m.step({ number: 2 })}</h4>
				<p class="text-surface-900">{m.enterCodeGeneratedByApp()}</p>
				<!-- Enable for debugging: -->
				<SuperForm
					dataType="json"
					action={formAction}
					data={_form}
					validators={zod(activateTOTPSchema)}
					
					class="modal-form {cForm}"
					validationMethod="onsubmit"
				>
					{#snippet children({ form })}
										<!-- prettier-ignore -->
						<OTPInput {form} field="code" />
						<footer class="modal-footer {parent.regionFooter}">
							<button
								class="btn variant-filled-primary w-full"
								data-testid="activate-totp-confirm-button"
								type="submit">{m.enableTOTP()}</button
							>
						</footer>
														{/snippet}
								</SuperForm>
			</div>
		</article>
	</div>
{/if}
