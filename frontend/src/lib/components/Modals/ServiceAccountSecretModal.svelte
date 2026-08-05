<script lang="ts">
	import { copy } from '@svelte-put/copy';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		clientId: string;
		clientSecret: string;
	}

	let { parent, clientId, clientSecret }: Props = $props();

	let copiedField = $state('');
	let secretRevealed = $state(false);

	function handleCopy(field: string) {
		copiedField = field;
		setTimeout(() => {
			copiedField = '';
		}, 2000);
	}

	function close() {
		if (parent && typeof parent.onConfirm === 'function') {
			parent.onConfirm();
		} else {
			modalStore.close();
		}
	}

	// Base Classes
	const cBase = 'card bg-surface-50-950 p-4 w-fit shadow-xl space-y-4 max-w-[80ch] overflow-auto';
	const cHeader = 'text-2xl font-bold';
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? m.clientSecret()}</header>
		<div class="card p-4 preset-tonal-secondary flex flex-row items-center">
			<i class="fa-solid fa-bell mr-2 text-secondary-800"></i>{m.clientSecretOnlyDisplayedOnce()}
		</div>
		<div class="space-y-2">
			<label class="label font-semibold" for="service-account-client-id">{m.clientId()}</label>
			<div class="flex flex-row gap-2 items-stretch">
				<input
					id="service-account-client-id"
					type="text"
					readonly
					value={clientId}
					class="input font-mono text-sm px-3 py-2 flex-1 select-all"
					onfocus={(e) => e.currentTarget.select()}
					data-testid="client-id-value"
				/>
				<button
					type="button"
					class="btn preset-filled-primary-500 px-4"
					use:copy={{ text: clientId }}
					onclick={() => handleCopy('client_id')}
				>
					{#if copiedField === 'client_id'}
						<i class="fa-solid fa-check mr-2"></i>{m.copied()}
					{:else}
						<i class="fa-solid fa-copy mr-2"></i>{m.copy()}
					{/if}
				</button>
			</div>
		</div>
		<div class="space-y-2">
			<label class="label font-semibold" for="service-account-client-secret"
				>{m.clientSecret()}</label
			>
			<div class="flex flex-row gap-2 items-stretch">
				<input
					id="service-account-client-secret"
					type={secretRevealed ? 'text' : 'password'}
					readonly
					value={clientSecret}
					class="input font-mono text-sm px-3 py-2 flex-1 select-all"
					onfocus={(e) => e.currentTarget.select()}
					data-testid="client-secret-value"
				/>
				<button
					type="button"
					class="btn preset-tonal-surface border border-surface-300-700 px-3"
					onclick={() => (secretRevealed = !secretRevealed)}
					aria-label={secretRevealed ? m.hide() : m.show()}
					data-testid="toggle-client-secret-visibility"
				>
					<i class="fa-solid {secretRevealed ? 'fa-eye-slash' : 'fa-eye'}"></i>
				</button>
				<button
					type="button"
					class="btn preset-filled-primary-500 px-4"
					use:copy={{ text: clientSecret }}
					onclick={() => handleCopy('client_secret')}
				>
					{#if copiedField === 'client_secret'}
						<i class="fa-solid fa-check mr-2"></i>{m.copied()}
					{:else}
						<i class="fa-solid fa-copy mr-2"></i>{m.copy()}
					{/if}
				</button>
			</div>
		</div>
		<footer class="modal-footer {parent?.regionFooter ?? ''}">
			<button class="btn preset-filled-primary-500 w-full" type="button" onclick={close}
				>{m.done()}</button
			>
		</footer>
	</div>
{/if}
