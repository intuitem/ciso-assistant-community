<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		cell: boolean | null | undefined;
		meta?: Record<string, any>;
		[key: string]: any;
	}

	let { cell, meta }: Props = $props();
	// `false` is also the default: with no recorded decision it means nobody assessed it.
	const assessed = $derived(cell === true || meta?.dpia_required_source !== '');
</script>

{#if cell === true}
	<span class="badge preset-tonal-error">{m.dpiaRequiredYes()}</span>
{:else if cell === false && !assessed}
	<span class="badge preset-tonal-surface">{m.notAssessed()}</span>
{:else if cell === false}
	<span class="badge preset-tonal-success">{m.dpiaRequiredNo()}</span>
{/if}
