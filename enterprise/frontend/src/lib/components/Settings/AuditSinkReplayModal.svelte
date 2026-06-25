<script lang="ts">
	import { enhance } from '$app/forms';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { m } from '$paraglide/messages';

	const cBase = 'card bg-surface-50 p-4 shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		parent: any;
		id: string;
		formAction?: string;
		[key: string]: any;
	}

	const modalStore: ModalStore = getModalStore();

	let { parent, id, formAction = '?/replayAuditSink' }: Props = $props();

	let since = $state('');
	let until = $state('');
</script>

{#if $modalStore[0]}
	<div class="w-lg {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? m.replayAuditEvents()}
		</header>
		<p class="text-sm text-gray-500">{m.replayAuditEventsHelpText()}</p>
		<form
			method="POST"
			action={formAction}
			class="flex flex-col space-y-3"
			use:enhance={() => {
				return async ({ result, update }) => {
					await update();
					if (result.type === 'success' && typeof parent?.onConfirm === 'function')
						parent.onConfirm();
				};
			}}
		>
			<input type="hidden" name="id" value={id} />
			<label class="label">
				<span>{m.replaySince()}</span>
				<input class="input" type="datetime-local" name="since" bind:value={since} required />
			</label>
			<label class="label">
				<span>{m.replayUntilOptional()}</span>
				<input class="input" type="datetime-local" name="until" bind:value={until} />
			</label>
			<div class="flex flex-row justify-between space-x-4">
				<button
					class="btn bg-gray-400 text-white font-semibold w-full"
					type="button"
					onclick={(event) => parent.onClose(event)}>{m.cancel()}</button
				>
				<button class="btn preset-filled-primary-500 font-semibold w-full" type="submit"
					>{m.replayAuditEvents()}</button
				>
			</div>
		</form>
	</div>
{/if}
