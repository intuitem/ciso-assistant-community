<script lang="ts">
	import {
		BaseEdge,
		EdgeLabel,
		getBezierPath,
		useInternalNode,
		useSvelteFlow,
		type EdgeProps
	} from '@xyflow/svelte';
	import { m } from '$paraglide/messages';

	// The one edge used everywhere (n8n behavior): a plain bezier while the
	// target sits forward of the source, switching to a rounded step detour
	// when the target is behind — the loop-back case, or any node dragged
	// behind its predecessor. The detour picks its horizontal channel from the
	// node rectangles (through the vertical gap between them when one exists,
	// otherwise around the outside), so it never crosses itself.
	let {
		id,
		source,
		target,
		sourceX,
		sourceY,
		targetX,
		targetY,
		sourcePosition,
		targetPosition,
		markerEnd,
		style,
		selected,
		deletable
	}: EdgeProps = $props();

	// An edge instance's endpoints never change (edges are keyed by id), so
	// capturing the initial values is correct here.
	// svelte-ignore state_referenced_locally
	const sourceNode = useInternalNode(source);
	// svelte-ignore state_referenced_locally
	const targetNode = useInternalNode(target);

	const { deleteElements } = useSvelteFlow();
	let hovered = $state(false);

	const RADIUS = 12;
	const OFFSET = 28;
	const CLEARANCE = 32;

	function rect(node: { current?: any }, fallbackX: number, fallbackY: number) {
		const internals = node.current;
		if (!internals) {
			return { top: fallbackY - 20, bottom: fallbackY + 20, left: fallbackX, right: fallbackX };
		}
		const { x, y } = internals.internals.positionAbsolute;
		return {
			top: y,
			bottom: y + (internals.measured?.height ?? 40),
			left: x,
			right: x + (internals.measured?.width ?? 180)
		};
	}

	const geometry = $derived.by(() => {
		if (targetX >= sourceX + OFFSET) {
			const [bezier, labelX, labelY] = getBezierPath({
				sourceX,
				sourceY,
				sourcePosition,
				targetX,
				targetY,
				targetPosition
			});
			return { path: bezier, labelX, labelY };
		}

		const sourceRect = rect(sourceNode, sourceX, sourceY);
		const targetRect = rect(targetNode, targetX, targetY);

		// Horizontal channel: always dropped BELOW the source node (n8n rule) —
		// the mid-gap between the nodes is where forward beziers live, so
		// routing through it guarantees crossings. Pushed below the target too
		// when the channel would slice through its rectangle.
		let channelY = sourceRect.bottom + CLEARANCE;
		if (channelY > targetRect.top - CLEARANCE && channelY < targetRect.bottom + CLEARANCE) {
			channelY = Math.max(sourceRect.bottom, targetRect.bottom) + CLEARANCE;
		}

		const outX = sourceX + OFFSET;
		const inX = targetX - OFFSET;
		const r = Math.min(
			RADIUS,
			Math.abs(channelY - sourceY) / 2,
			Math.abs(targetY - channelY) / 2,
			Math.abs(outX - inX) / 2
		);
		const downFirst = channelY > sourceY ? 1 : -1;
		const upLast = targetY > channelY ? 1 : -1;
		const path = [
			`M ${sourceX} ${sourceY}`,
			`H ${outX - r}`,
			`Q ${outX} ${sourceY} ${outX} ${sourceY + r * downFirst}`,
			`V ${channelY - r * downFirst}`,
			`Q ${outX} ${channelY} ${outX - r} ${channelY}`,
			`H ${inX + r}`,
			`Q ${inX} ${channelY} ${inX} ${channelY + r * upLast}`,
			`V ${targetY - r * upLast}`,
			`Q ${inX} ${targetY} ${inX + r} ${targetY}`,
			`L ${targetX} ${targetY}`
		].join(' ');
		// Midpoint of the horizontal channel segment.
		return { path, labelX: (outX + inX) / 2, labelY: channelY };
	});
</script>

<BaseEdge
	path={geometry.path}
	{markerEnd}
	{style}
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
/>

{#if deletable && (hovered || selected)}
	<EdgeLabel x={geometry.labelX} y={geometry.labelY}>
		<button
			type="button"
			class="nopan nodrag flex h-5 w-5 items-center justify-center rounded-full bg-surface-200-800 text-surface-600-400 shadow-sm hover:bg-error-500 hover:text-white"
			title={m.delete()}
			data-testid="edge-delete"
			onmouseenter={() => (hovered = true)}
			onmouseleave={() => (hovered = false)}
			onclick={(e) => {
				e.stopPropagation();
				deleteElements({ edges: [{ id }] });
			}}
		>
			<i class="fa-solid fa-xmark text-[10px]"></i>
		</button>
	</EdgeLabel>
{/if}
