<script lang="ts">
	import { m } from '$paraglide/messages';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import OTPInput from '$lib/components/Forms/OTP/OTPInput.svelte';
	import QR from '@svelte-put/qr/svg/QR.svelte';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { activateTOTPSchema } from '../(third-party)/my-profile/settings/mfa/utils/schemas';
	import { startRegistration } from '@simplewebauthn/browser';
	import { invalidateAll } from '$app/navigation';

	let { data } = $props();

	type SetupMethod = 'choose' | 'totp' | 'webauthn';
	let method: SetupMethod = $state('choose');

	let webAuthnName = $state('');
	let webAuthnError: string | null = $state(null);
	let webAuthnLoading = $state(false);

	async function handleWebAuthnRegister() {
		if (!data.webauthnCreationOptions) return;
		webAuthnError = null;
		webAuthnLoading = true;

		try {
			const credential = await startRegistration({
				optionsJSON: data.webauthnCreationOptions.publicKey
			});

			const formData = new FormData();
			formData.set('name', webAuthnName || 'Security Key');
			formData.set('credential', JSON.stringify(credential));

			const response = await fetch('?/registerWebAuthn', {
				method: 'POST',
				body: formData
			});

			if (response.status === 303) {
				const location = response.headers.get('location');
				window.location.href = location || '/';
				return;
			}

			if (response.ok) {
				window.location.href = '/';
				return;
			}

			webAuthnError = m.webAuthnError();
		} catch (err: any) {
			if (err.name === 'NotAllowedError') {
				webAuthnError = m.webAuthnCancelled();
			} else {
				console.error('WebAuthn registration error:', err);
				webAuthnError = m.webAuthnError();
			}
		} finally {
			webAuthnLoading = false;
		}
	}
</script>

<div class="flex items-center justify-center min-h-screen bg-surface-100 p-4">
	<div class="card bg-surface-50 p-8 shadow-xl space-y-6 overflow-hidden max-w-2xl">
		<header class="text-center space-y-4">
			<i class="fa-solid fa-shield-halved text-4xl text-primary-500"></i>
			<h2 class="h2 font-bold">{m.setupMfa()}</h2>
			<p class="text-surface-600">{m.mfaRequiredByAdmin()}</p>
		</header>

		{#if method === 'choose'}
			<div class="flex flex-col sm:flex-row gap-4 justify-center">
				<button
					class="card p-6 bg-inherit hover:bg-surface-200 cursor-pointer flex flex-col items-center space-y-3 flex-1"
					onclick={() => (method = 'totp')}
				>
					<i class="fa-solid fa-mobile-screen-button text-3xl text-primary-500"></i>
					<h4 class="h4 font-medium">{m.authenticatorApp()}</h4>
					<p class="text-sm text-surface-600 text-center">{m.authenticatorAppDescription()}</p>
				</button>

				{#if data.webauthnCreationOptions}
					<button
						class="card p-6 bg-inherit hover:bg-surface-200 cursor-pointer flex flex-col items-center space-y-3 flex-1"
						onclick={() => (method = 'webauthn')}
					>
						<i class="fa-solid fa-fingerprint text-3xl text-primary-500"></i>
						<h4 class="h4 font-medium">{m.securityKeys()}</h4>
						<p class="text-sm text-surface-600 text-center">{m.securityKeyDescription()}</p>
					</button>
				{/if}
			</div>
		{:else if method === 'totp'}
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
			<button class="btn hover:underline text-sm" onclick={() => (method = 'choose')}>
				<i class="fa-solid fa-arrow-left mr-1"></i>
				{m.back()}
			</button>
		{:else if method === 'webauthn'}
			<div class="flex flex-col items-center space-y-6">
				<i class="fa-solid fa-fingerprint text-5xl text-primary-500"></i>
				<p class="text-surface-900 text-center max-w-md">{m.securityKeyDescription()}</p>
				<label class="label w-full max-w-xs">
					<span>{m.securityKeyName()}</span>
					<input
						class="input"
						type="text"
						bind:value={webAuthnName}
						placeholder="Security Key"
						maxlength="100"
					/>
				</label>
				{#if webAuthnError}
					<p class="text-sm text-error-500">{webAuthnError}</p>
				{/if}
				<button
					class="btn preset-filled-primary-500"
					disabled={webAuthnLoading}
					onclick={handleWebAuthnRegister}
				>
					{#if webAuthnLoading}
						<i class="fa-solid fa-spinner fa-spin mr-2"></i>
					{:else}
						<i class="fa-solid fa-fingerprint mr-2"></i>
					{/if}
					{m.addSecurityKey()}
				</button>
			</div>
			<button class="btn hover:underline text-sm" onclick={() => (method = 'choose')}>
				<i class="fa-solid fa-arrow-left mr-1"></i>
				{m.back()}
			</button>
		{/if}
	</div>
</div>
