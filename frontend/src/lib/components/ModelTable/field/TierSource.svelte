<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		cell: string | null | undefined;
		[key: string]: any;
	}

	let { cell }: Props = $props();

	// The raw values ("assessment"…) collide with generic message keys
	// ("assessment" is "Audit" in French): name each source on purpose.
	const LABELS: Record<string, () => string> = {
		assessment: m.tierSourceAssessment,
		override: m.tierSourceOverride,
		manual: m.tierSourceManual
	};
</script>

{#if cell}{LABELS[cell]?.() ?? cell}{/if}
