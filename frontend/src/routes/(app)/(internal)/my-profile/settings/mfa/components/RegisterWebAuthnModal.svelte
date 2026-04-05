<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { startRegistration } from '@simplewebauthn/browser';
	import { invalidateAll } from '$app/navigation';

	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		parent: any;
		creationOptions: any;
		formAction: string;
	}

	let { parent, creationOptions, formAction }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	let name = $state('');
	let error: string | null = $state(null);
	let loading = $state(false);

	async function handleRegister() {
		error = null;
		loading = true;

		try {
			const credential = await startRegistration({
				optionsJSON: creationOptions.publicKey
			});

			const formData = new FormData();
			formData.set('name', name || 'Security Key');
			formData.set('credential', JSON.stringify(credential));

			const response = await fetch(formAction, {
				method: 'POST',
				body: formData
			});

			if (response.ok) {
				modalStore.close();
				await invalidateAll();
			} else {
				error = m.webAuthnError();
			}
		} catch (err: any) {
			if (err.name === 'NotAllowedError') {
				error = m.webAuthnCancelled();
			} else {
				console.error('WebAuthn registration error:', err);
				error = m.webAuthnError();
			}
		} finally {
			loading = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? m.addSecurityKey()}</header>
		<article>{$modalStore[0].body ?? ''}</article>
		<div class="flex flex-col space-y-4">
			<label class="label">
				<span>{m.securityKeyName()}</span>
				<input
					class="input"
					type="text"
					bind:value={name}
					placeholder="Security Key"
					maxlength="100"
				/>
			</label>
			{#if error}
				<p class="text-sm text-error-500">{error}</p>
			{/if}
			<footer class="flex justify-end gap-2">
				<button
					type="button"
					class="btn preset-outlined-surface-500"
					onclick={() => modalStore.close()}
				>
					{m.cancel()}
				</button>
				<button
					type="button"
					class="btn preset-filled-primary-500"
					disabled={loading}
					onclick={handleRegister}
				>
					{#if loading}
						<i class="fa-solid fa-spinner fa-spin mr-2"></i>
					{:else}
						<i class="fa-solid fa-fingerprint mr-2"></i>
					{/if}
					{m.addSecurityKey()}
				</button>
			</footer>
		</div>
	</div>
{/if}
