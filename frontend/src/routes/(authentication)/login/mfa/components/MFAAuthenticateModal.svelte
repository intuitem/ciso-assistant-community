<script lang="ts">
	import OTPInput from '$lib/components/Forms/OTP/OTPInput.svelte';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { mfaAuthenticateSchema } from '../utils/schemas';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { m } from '$paraglide/messages';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { superForm } from 'sveltekit-superforms';
	import { startAuthentication } from '@simplewebauthn/browser';

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
		mfaTypes?: string[];
	}

	let { parent, _form, formAction, mfaTypes = ['totp'] }: Props = $props();

	type MfaMode = 'totp' | 'recovery_code' | 'webauthn';
	let mode: MfaMode = $state(mfaTypes.includes('webauthn') ? 'webauthn' : 'totp');

	let webAuthnError: string | null = $state(null);
	let webAuthnLoading = $state(false);

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

	async function handleWebAuthn() {
		webAuthnError = null;
		webAuthnLoading = true;

		try {
			// Fetch challenge from server proxy
			const challengeRes = await fetch('/login/mfa/webauthn');
			const challengeData = await challengeRes.json();

			if (challengeData.error) {
				webAuthnError = m.webAuthnError();
				return;
			}

			// Start WebAuthn authentication via browser API
			const credential = await startAuthentication({
				optionsJSON: challengeData.data.request_options.publicKey
			});

			// Submit credential via form action
			const formData = new FormData();
			formData.set('credential', JSON.stringify(credential));

			const response = await fetch(`?/mfaAuthenticateWebAuthn`, {
				method: 'POST',
				body: formData
			});

			if (response.ok && response.redirected) {
				window.location.href = response.url;
				return;
			}

			// SvelteKit form actions return 303 redirect on success
			if (response.status === 303) {
				const location = response.headers.get('location');
				window.location.href = location || '/';
				return;
			}

			// If we get here, something went wrong
			const result = await response.json();
			if (result?.error) {
				webAuthnError = m.webAuthnError();
			} else {
				// Success — redirect
				window.location.href = '/';
			}
		} catch (err: any) {
			if (err.name === 'NotAllowedError') {
				webAuthnError = m.webAuthnCancelled();
			} else {
				console.error('WebAuthn authentication error:', err);
				webAuthnError = m.webAuthnError();
			}
		} finally {
			webAuthnLoading = false;
		}
	}

	$effect(() => {
		if (mode === 'webauthn') {
			handleWebAuthn();
		}
	});
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>
		<article class="flex flex-col space-y-4 items-center">
			{#if mode === 'webauthn'}
				<div class="flex flex-col items-center space-y-4 p-4">
					<i class="fa-solid fa-fingerprint text-4xl text-primary-500"></i>
					{#if webAuthnLoading}
						<p class="text-sm text-surface-800">{m.webAuthnAuthenticating()}</p>
					{/if}
					{#if webAuthnError}
						<p class="text-sm text-error-500">{webAuthnError}</p>
						<button
							type="button"
							class="btn preset-outlined-primary-500"
							onclick={() => handleWebAuthn()}
						>
							{m.useSecurityKey()}
						</button>
					{/if}
				</div>
			{:else}
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
						{#if mode === 'totp'}
							<OTPInput {form} field="code" />
						{:else}
							<TextField {form} field="code" label={m.recoveryCode()} />
						{/if}
						<footer class="modal-footer {parent.regionFooter}">
							<button
								type="submit"
								class="btn preset-filled-primary-500"
								data-testid="mfa-authenticate-confirm-button"
							>
								{m.login()}
							</button>
						</footer>
					{/snippet}
				</SuperForm>
			{/if}
			<div class="flex flex-wrap gap-2 justify-center">
				{#if mode !== 'totp' && mfaTypes.includes('totp')}
					<button type="button" onclick={() => (mode = 'totp')} class="btn hover:underline text-sm">
						{m.loginUsingTOTP()}
					</button>
				{/if}
				{#if mode !== 'recovery_code' && mfaTypes.includes('recovery_codes')}
					<button
						type="button"
						onclick={() => (mode = 'recovery_code')}
						class="btn hover:underline text-sm"
					>
						{m.loginUsingRecoveryCode()}
					</button>
				{/if}
				{#if mode !== 'webauthn' && mfaTypes.includes('webauthn')}
					<button
						type="button"
						onclick={() => (mode = 'webauthn')}
						class="btn hover:underline text-sm"
					>
						<i class="fa-solid fa-fingerprint mr-1"></i>
						{m.useSecurityKey()}
					</button>
				{/if}
			</div>
		</article>
	</div>
{/if}
