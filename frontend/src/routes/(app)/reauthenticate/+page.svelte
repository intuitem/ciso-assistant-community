<script lang="ts">
	import { m } from '$paraglide/messages';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import OTPInput from '$lib/components/Forms/OTP/OTPInput.svelte';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { reauthenticateSchema } from '$lib/utils/schemas';
	import { startAuthentication } from '@simplewebauthn/browser';
	import { tick } from 'svelte';

	let { data } = $props();

	let credential = $state('');
	let webAuthnError: string | null = $state(null);

	async function useSecurityKey(event: MouseEvent) {
		const formElement = (event.currentTarget as HTMLButtonElement).form;
		webAuthnError = null;
		try {
			const assertion = await startAuthentication({
				optionsJSON: data.requestOptions.publicKey
			});
			credential = JSON.stringify(assertion);
			await tick();
			formElement?.requestSubmit();
		} catch (err: any) {
			webAuthnError = err.name === 'NotAllowedError' ? m.webAuthnCancelled() : m.webAuthnError();
		}
	}
</script>

<div class="flex items-center justify-center min-h-screen bg-surface-100 p-4">
	<div class="card bg-surface-50 p-8 shadow-xl space-y-6 max-w-md w-full">
		<header class="text-center space-y-4">
			<i class="fa-solid fa-lock text-4xl text-primary-500"></i>
			<p class="text-surface-600">{m.reauthenticateForSensitiveAction()}</p>
		</header>
		<SuperForm
			data={data.form}
			validators={zod(reauthenticateSchema)}
			class="space-y-4"
			validationMethod="onsubmit"
		>
			{#snippet children({ form, errors })}
				{#if data.method === 'webauthn'}
					<input type="hidden" name="credential" value={credential} />
					{#each [webAuthnError, ...(errors.credential ?? [])].filter(Boolean) as error}
						<p class="text-sm text-error-500">{error}</p>
					{/each}
					<button
						class="btn preset-filled-primary-500 w-full"
						data-testid="reauthenticate-button"
						type="button"
						disabled={!data.requestOptions}
						onclick={useSecurityKey}
					>
						<i class="fa-solid fa-fingerprint mr-2"></i>{m.useSecurityKey()}
					</button>
				{:else}
					{#if data.method === 'code'}
						<OTPInput {form} field="code" />
					{:else}
						<TextField type="password" {form} field="password" label={m.password()} />
					{/if}
					<button
						class="btn preset-filled-primary-500 w-full"
						data-testid="reauthenticate-button"
						type="submit">{m.confirm()}</button
					>
				{/if}
			{/snippet}
		</SuperForm>
	</div>
</div>
