<script lang="ts">
	import { untrack } from 'svelte';
	import { Tween } from 'svelte/motion';
	import { cubicInOut } from 'svelte/easing';
	import type { Point, TrajectoryDot } from './trajectory';

	interface Props {
		dot: TrajectoryDot;
		stageIndex: number;
		delay?: number;
		duration?: number;
		flag?: 'overdue' | 'unscheduled' | null;
		highlighted?: boolean;
		dimmed?: boolean;
	}

	let {
		dot,
		stageIndex,
		delay = 0,
		duration = 900,
		flag = null,
		highlighted = false,
		dimmed = false
	}: Props = $props();

	let ringClass = $derived(
		dot.worsened[stageIndex]
			? 'ring-red-500 animate-pulse'
			: flag === 'overdue'
				? 'ring-amber-500'
				: highlighted
					? 'ring-primary-500'
					: 'ring-white'
	);

	const position = untrack(
		() =>
			new Tween(
				dot.positions[stageIndex] ?? dot.positions.find((p) => p !== null) ?? { x: 50, y: 50 },
				{
					duration,
					easing: cubicInOut
				}
			)
	);

	$effect(() => {
		const target = dot.positions[stageIndex];
		if (target) position.set(target, { delay, duration });
	});

	let hovered = $state(false);
	let visible = $derived(dot.positions[stageIndex] !== null);
	let moving = $derived(
		position.current.x !== position.target.x || position.current.y !== position.target.y
	);

	let history = $derived(dot.positions.slice(0, stageIndex).filter((p): p is Point => p !== null));
	let trail = $derived(
		(hovered ? history : history.slice(-1))
			.concat(position.current)
			.map((p) => `${p.x},${p.y}`)
			.join(' ')
	);
</script>

{#if visible && history.length > 0}
	<svg
		class="absolute inset-0 w-full h-full pointer-events-none overflow-visible transition-opacity duration-500 {hovered
			? 'opacity-80'
			: moving
				? 'opacity-40'
				: 'opacity-0'}"
		viewBox="0 0 100 100"
		preserveAspectRatio="none"
	>
		<polyline
			points={trail}
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-dasharray={hovered ? 'none' : '4 3'}
			vector-effect="non-scaling-stroke"
			class="text-surface-900"
		/>
	</svg>
	{#if hovered}
		{#each history as ghost}
			<span
				class="absolute w-3 h-3 rounded-full border-2 border-surface-900 bg-white/70 pointer-events-none"
				style="left: {ghost.x}%; top: {ghost.y}%; transform: translate(-50%, -50%);"
			></span>
		{/each}
	{/if}
{/if}
<a
	href="/risk-scenarios/{dot.id}"
	title="{dot.label} - {dot.name}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	onfocus={() => (hovered = true)}
	onblur={() => (hovered = false)}
	class="absolute pointer-events-auto flex items-center justify-center min-w-7 h-7 px-1 rounded-full bg-surface-900 text-white text-[10px] font-semibold shadow-md ring-2 transition-[opacity,box-shadow,scale] duration-300 hover:scale-110 {hovered ||
	highlighted
		? 'z-20'
		: 'z-10'} {highlighted ? 'scale-125' : ''} {flag === 'unscheduled'
		? 'outline-2 outline-dashed outline-offset-2 outline-surface-500'
		: ''} {ringClass}"
	style="left: {position.current.x}%; top: {position.current
		.y}%; transform: translate(-50%, -50%); opacity: {visible ? (dimmed ? 0.3 : 1) : 0};"
	data-testid="trajectory-dot"
>
	<span class="truncate max-w-16">{dot.label}</span>
</a>
