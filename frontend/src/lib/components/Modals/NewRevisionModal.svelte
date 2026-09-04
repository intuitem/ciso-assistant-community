<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		parent: any;
		initialName: string;
		initialVersion: string;
		onSubmit: (values: { name: string; version: string }) => void;
	}

	let { parent, initialName, initialVersion, onSubmit }: Props = $props();

	const cBase =
		'card bg-surface-100-900 border border-surface-500 p-4 w-full max-w-xl shadow-xl space-y-4';

	let name = $state(initialName);
	let version = $state(initialVersion);
	// name + version identify an assessment within its domain, so a revision has to
	// move at least one of them.
	const unchanged = $derived(name.trim() === initialName && version.trim() === initialVersion);

	function submit(event: Event) {
		event.preventDefault();
		if (!name.trim() || !version.trim() || unchanged) return;
		modalStore.close();
		onSubmit({ name: name.trim(), version: version.trim() });
	}
</script>

{#if $modalStore[0]}
	<div class="modal-new-revision {cBase}">
		<div class="flex items-center justify-between">
			<header class="text-2xl font-bold">{m.newRevision()}</header>
			<button
				type="button"
				aria-label={m.close()}
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>
		<p class="text-sm text-surface-600-400">{m.newRevisionHelpText()}</p>
		<form class="space-y-4" onsubmit={submit}>
			<label class="block">
				<span class="text-sm font-semibold">{m.name()}</span>
				<input class="input w-full mt-1" bind:value={name} required />
			</label>
			<label class="block">
				<span class="text-sm font-semibold">{m.version()}</span>
				<input
					class="input w-full mt-1"
					bind:value={version}
					required
					data-testid="revision-version"
				/>
			</label>
			{#if unchanged}
				<p class="text-xs text-error-500">{m.revisionNeedsNewNameOrVersion()}</p>
			{/if}
			<div class="flex justify-end space-x-2">
				<button
					type="button"
					class="btn preset-tonal-surface border border-surface-500"
					onclick={parent.onClose}
				>
					{m.cancel()}
				</button>
				<button type="submit" class="btn preset-filled-primary-500" disabled={unchanged}>
					{m.create()}
				</button>
			</div>
		</form>
	</div>
{/if}
