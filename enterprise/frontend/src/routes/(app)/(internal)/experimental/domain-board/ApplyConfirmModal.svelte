<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';

	interface Props {
		parent: any;
		/** One line per staged change — moves and deletions — formatted for reading. */
		moves: string[];
		/** true when the draft removes domains as well as moving them */
		destructive?: boolean;
		onConfirm: () => void;
	}

	let { parent, moves, destructive = false, onConfirm }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	// Same contract as PromptConfirmModal: type the localized word for "yes".
	const yes = m.yes().toLowerCase();
	let userInput = $state('');
	const canConfirm = $derived(userInput.trim().toLowerCase() === yes);

	function confirm() {
		if (!canConfirm) return;
		modalStore.close();
		onConfirm();
	}
</script>

<div
	class="card w-fit max-w-4xl space-y-4 border border-surface-500 bg-surface-100-900 p-4 shadow-xl"
>
	<header class="text-2xl font-bold">
		{moves.length === 1 ? 'Apply 1 change' : `Apply ${moves.length} changes`}
	</header>

	<div class="max-h-64 overflow-y-auto rounded border border-surface-300-700 bg-surface-50-950 p-3">
		<ul class="space-y-1 font-mono text-xs text-surface-700-300">
			{#each moves as move}
				<li>{move}</li>
			{/each}
		</ul>
	</div>

	<article
		class="rounded border border-warning-200-800 bg-warning-50-950 px-3 py-2 text-sm text-warning-700-300"
	>
		<i class="fa-solid fa-triangle-exclamation mr-1"></i>
		This changes access, not just the drawing. A role held on a new parent reaches everything inside the
		domain moved under it, and access inherited from the old parent is lost. All moves are applied together,
		and there is no undo — reverting means drafting the moves back.
	</article>

	{#if destructive}
		<article
			class="rounded border border-error-200-800 bg-error-50-950 px-3 py-2 text-sm text-error-700-300"
		>
			<i class="fa-solid fa-trash mr-1"></i>
			This draft <strong>deletes</strong> domains. Only empty ones can be staged, and the server checks
			again before removing them — but a deleted domain is gone for good.
		</article>
	{/if}

	<form
		class="flex flex-col space-y-3"
		onsubmit={(e) => {
			e.preventDefault();
			confirm();
		}}
	>
		<p class="text-sm font-medium text-error-600-400">{m.confirmYes({ word: m.yes() })}</p>
		<input
			class="input"
			type="text"
			bind:value={userInput}
			placeholder={m.confirmYesPlaceHolder({ word: m.yes() })}
			aria-label={m.confirmYes({ word: m.yes() })}
		/>
		<div class="flex justify-end gap-2">
			<button type="button" class="btn preset-tonal-surface" onclick={parent.onClose}>
				{m.cancel()}
			</button>
			<button
				type="submit"
				class="btn {destructive ? 'preset-filled-error-500' : 'preset-filled-warning-500'}"
				disabled={!canConfirm}
			>
				{m.apply()}
			</button>
		</div>
	</form>
</div>
