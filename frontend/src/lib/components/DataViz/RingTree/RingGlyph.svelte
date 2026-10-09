<script lang="ts">
	import type { RingColor } from './types';

	interface Props {
		own?: number | null;
		ownSegments?: { fraction: number; color: string }[];
		faint?: boolean;
		branch: number | null;
		showBranch?: boolean;
		empty?: boolean;
		color: RingColor;
		rOut: number;
		rIn: number;
		wOut: number;
		wIn: number;
	}

	let {
		own,
		ownSegments,
		faint = false,
		branch,
		showBranch = true,
		empty = false,
		color,
		rOut,
		rIn,
		wOut,
		wIn
	}: Props = $props();

	const cOut = $derived(2 * Math.PI * rOut);
	const cIn = $derived(2 * Math.PI * rIn);
	const slices = $derived.by(() => {
		let start = 0;
		return (ownSegments ?? []).map((s) => {
			const slice = { ...s, start };
			start += s.fraction;
			return slice;
		});
	});
</script>

{#if showBranch}
	<circle
		r={rOut}
		fill="none"
		stroke="currentColor"
		stroke-opacity="0.12"
		stroke-width={wOut}
		stroke-dasharray={empty ? `${wOut + 1} ${wOut + 1}` : undefined}
	/>
	{#if branch !== null}
		<circle
			r={rOut}
			fill="none"
			stroke={color(branch)}
			stroke-width={wOut}
			stroke-linecap="round"
			stroke-dasharray="{(branch / 100) * cOut} {cOut}"
			transform="rotate(-90)"
		/>
	{/if}
{/if}
{#if own !== undefined}
	<circle
		r={rIn}
		fill="none"
		stroke="currentColor"
		stroke-opacity={faint ? 0.3 : 0.12}
		stroke-width={wIn}
		stroke-dasharray={faint ? `${wIn * 0.35} ${wIn * 0.35}` : undefined}
	/>
	{#if ownSegments}
		{#each slices as s (s.color)}
			<circle
				r={rIn}
				fill="none"
				stroke={s.color}
				stroke-opacity={faint ? 0.35 : 1}
				stroke-width={wIn}
				stroke-dasharray="{s.fraction * cIn} {cIn}"
				stroke-dashoffset={-s.start * cIn}
				transform="rotate(-90)"
			/>
		{/each}
	{:else if own !== null}
		<circle
			r={rIn}
			fill="none"
			stroke={color(own)}
			stroke-opacity={faint ? 0.35 : 1}
			stroke-width={wIn}
			stroke-dasharray="{(own / 100) * cIn} {cIn}"
			transform="rotate(-90)"
		/>
	{/if}
{/if}
