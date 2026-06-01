<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		/** Warning text shown next to confirm/cancel when active */
		message?: string;
		/** Callback when the user confirms the action */
		onconfirm: () => void;
		/** Label for the confirm button (default "Confirm") */
		confirmLabel?: string;
		/** Additional CSS classes on the initial trigger button */
		triggerClass?: string;
		/** Additional CSS classes on the confirm button */
		confirmClass?: string;
	}

	let {
		message = '',
		onconfirm,
		confirmLabel,
		triggerClass = 'text-gray-300 hover:text-red-500 text-xs transition-colors',
		confirmClass = 'text-xs text-red-600 font-medium'
	}: Props = $props();

	let active = $state(false);
</script>

{#if active}
	{#if message}
		<span class="text-xs text-red-600 font-medium">{message}</span>
	{/if}
	<button
		type="button"
		class={confirmClass}
		onclick={() => {
			onconfirm();
			active = false;
		}}
	>
		{confirmLabel ?? m.confirm()}
	</button>
	<button type="button" class="text-xs text-gray-500" onclick={() => (active = false)}>
		{m.cancel()}
	</button>
{:else}
	<button type="button" class={triggerClass} onclick={() => (active = true)}>
		<i class="fa-solid fa-trash"></i>
	</button>
{/if}
