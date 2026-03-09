<script lang="ts">
	import { m } from '$paraglide/messages';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import OTPInput from '$lib/components/Forms/OTP/OTPInput.svelte';
	import QR from '@svelte-put/qr/svg/QR.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import { activateTOTPSchema } from '../(internal)/my-profile/settings/mfa/utils/schemas';

	let { data } = $props();
</script>

<div class="flex items-center justify-center min-h-screen bg-surface-100 p-4">
	<div class="card bg-surface-50 p-8 shadow-xl space-y-6 overflow-hidden">
		<header class="text-center space-y-4">
			<i class="fa-solid fa-shield-halved text-4xl text-primary-500"></i>
			<h2 class="h2 font-bold">{m.setupMfa()}</h2>
			<p class="text-surface-600">{m.mfaRequiredByAdmin()}</p>
		</header>

		<div class="flex flex-col md:flex-row gap-8">
			<div class="flex flex-col space-y-4 items-center min-w-0 max-w-xs">
				<h4 class="h4">{m.step({ number: 1 })}</h4>
				<p class="text-surface-900 text-center">{m.authenticatorAppDescription()}</p>
				{#if data.totp?.totp_url}
					<QR
						data={data.totp.totp_url.replace(
							/issuer=[^&]+/,
							'issuer=' + encodeURIComponent('CISO Assistant')
						)}
						anchorInnerFill="black"
						anchorOuterFill="black"
						width="250"
						height="250"
					/>

					<div class="flex items-center justify-center w-full space-x-2">
						<hr class="w-32 bg-gray-200 border-0" />
						<span class="text-gray-600 text-sm">{m.or()}</span>
						<hr class="w-32 bg-gray-200 border-0" />
					</div>

					<div>
						<p class="text-center text-surface-900">{m.enterTOTPCodeManually()}</p>
						<p class="text-center font-mono text-sm break-all">{data.totp.secret}</p>
					</div>
				{/if}
			</div>

			<div class="hidden md:block w-px bg-surface-300 self-stretch"></div>

			<div class="flex flex-col space-y-4 items-center min-w-0 self-center">
				<h4 class="h4">{m.step({ number: 2 })}</h4>
				<p class="text-surface-900 text-center">{m.enterCodeGeneratedByApp()}</p>
				<SuperForm
					dataType="json"
					action="?/activateTOTP"
					data={data.activateTOTPForm}
					validators={zod(activateTOTPSchema)}
					class="p-4 space-y-4 rounded-container w-full"
					validationMethod="onsubmit"
				>
					{#snippet children({ form })}
						<OTPInput {form} field="code" />
						<button
							class="btn preset-filled-primary-500 w-full"
							data-testid="activate-totp-confirm-button"
							type="submit">{m.enableTOTP()}</button
						>
					{/snippet}
				</SuperForm>
			</div>
		</div>
	</div>
</div>
