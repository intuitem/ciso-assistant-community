<script lang="ts">
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { m } from '#paraglide/messages.js';
	import { displayScoreColor, formatScoreValue, roundScore } from '#lib/utils/helpers.js';

	// The maturity (average of the implementation and documentation scores) as a
	// ring after the two score rings of the audit tree and the requirement page.
	interface Props {
		value: number;
		min: number;
		max: number;
		small?: boolean;
	}

	let { value, min, max, small = false }: Props = $props();
</script>

<div class="relative shrink-0" title={m.maturity()} data-testid="maturity-ring">
	<Progress value={formatScoreValue(value, max, false, min)} min={0} max={100}>
		<Progress.Circle class={small ? '[--size:--spacing(10)]' : '[--size:--spacing(12)]'}>
			<Progress.CircleTrack />
			<Progress.CircleRange class={displayScoreColor(value, max, false, min)} />
		</Progress.Circle>
		<div class="absolute inset-0 flex items-center justify-center">
			<span class="text-xs font-bold">{roundScore(value)}</span>
		</div>
	</Progress>
</div>
