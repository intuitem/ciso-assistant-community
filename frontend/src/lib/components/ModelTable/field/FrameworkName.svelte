<script lang="ts">
	import { m } from '$paraglide/messages';
	interface Props {
		cell: string;
		[key: string]: any;
	}

	let { cell, ...rest }: Props = $props();

	let hasUpdate = $derived(rest.meta.has_update);
</script>

{#if hasUpdate}
	<i title={m.updateAvailable()} class="fa-solid fa-circle-up text-success-600-400"></i>
{/if}

{cell}

{#if hasUpdate}
	({m.updateAvailable()})
{/if}
