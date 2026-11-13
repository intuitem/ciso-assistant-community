<script lang="ts">
	interface Props {
		values: number[];
		width?: number;
		height?: number;
		/** Tailwind text colour class; the line and its wash use currentColor. */
		class?: string;
	}

	let { values, width = 96, height = 28, class: className = '' }: Props = $props();

	const id = $props.id();
	const pad = 2;
	const points = $derived.by(() => {
		const min = Math.min(...values);
		const span = Math.max(...values) - min || 1;
		const step = (width - pad * 2) / Math.max(values.length - 1, 1);
		return values.map(
			(v, i) => [pad + i * step, height - pad - ((v - min) / span) * (height - pad * 2)] as const
		);
	});
	const line = $derived(points.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(''));
	const area = $derived(`${line}L${points.at(-1)![0]},${height}L${points[0][0]},${height}Z`);
</script>

<svg
	{width}
	{height}
	viewBox="0 0 {width} {height}"
	class="spark overflow-visible {className}"
	aria-hidden="true"
>
	<defs>
		<linearGradient id="wash-{id}" x1="0" x2="0" y1="0" y2="1">
			<stop offset="0" stop-color="currentColor" stop-opacity="0.22" />
			<stop offset="1" stop-color="currentColor" stop-opacity="0" />
		</linearGradient>
	</defs>
	<path d={area} fill="url(#wash-{id})" class="wash" />
	<path
		d={line}
		pathLength="1"
		fill="none"
		stroke="currentColor"
		stroke-width="1.75"
		stroke-linecap="round"
		stroke-linejoin="round"
		class="line"
	/>
	<circle cx={points.at(-1)![0]} cy={points.at(-1)![1]} r="2.5" fill="currentColor" class="dot" />
</svg>

<style>
	@media (prefers-reduced-motion: no-preference) {
		.line {
			stroke-dasharray: 1;
			animation: draw 900ms cubic-bezier(0.2, 0.7, 0.2, 1) both;
		}
		.wash,
		.dot {
			animation: fade 400ms 700ms ease-out both;
		}
	}
	@keyframes draw {
		from {
			stroke-dashoffset: 1;
		}
		to {
			stroke-dashoffset: 0;
		}
	}
	@keyframes fade {
		from {
			opacity: 0;
		}
	}
</style>
