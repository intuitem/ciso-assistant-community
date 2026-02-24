<script lang="ts">
	interface Props {
		id: string;
		x: number;
		y: number;
		label: string;
		iconClass?: string;
		stage: number;
		selected?: boolean;
		onPointerDownNode: (id: string, e: PointerEvent) => void;
		onPointerDownOutput: (id: string, e: PointerEvent) => void;
		onPointerUpInput: (id: string, e: PointerEvent) => void;
		onDelete: (id: string) => void;
	}

	let {
		id,
		x,
		y,
		label,
		iconClass = '',
		stage,
		selected = false,
		onPointerDownNode,
		onPointerDownOutput,
		onPointerUpInput,
		onDelete
	}: Props = $props();

	const WIDTH = 140;
	const HEIGHT = 50;

	const STAGE_STROKE: Record<number, string> = {
		0: '#ec4899', // pink
		1: '#8b5cf6', // violet
		2: '#f97316', // orange
		3: '#ef4444' // red
	};

	const STAGE_FILL: Record<number, string> = {
		0: '#fdf2f8', // pink-50
		1: '#f5f3ff', // violet-50
		2: '#fff7ed', // orange-50
		3: '#fef2f2' // red-50
	};

	let hovered = $state(false);

	const strokeColor = $derived(selected ? '#4D179A' : STAGE_STROKE[stage] ?? '#8b5cf6');
	const fillColor = $derived(hovered ? '#f8f6ff' : STAGE_FILL[stage] ?? '#ffffff');
	const strokeWidth = $derived(selected ? 2.5 : 1.5);

	// Handle size
	const HANDLE_R = 6;

	function wrapLabel(text: string, maxChars: number = 18): string[] {
		if (!text || text.length <= maxChars) return [text || ''];
		const words = text.split(' ');
		const lines: string[] = [];
		let current = '';
		for (const w of words) {
			if (current.length + w.length + 1 > maxChars) {
				if (current) lines.push(current);
				current = w;
			} else {
				current += (current ? ' ' : '') + w;
			}
		}
		if (current) lines.push(current);
		return lines;
	}

	const lines = $derived(wrapLabel(label));
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<g
	transform="translate({x}, {y})"
	class="action-node"
	style="cursor: grab"
	onpointerdown={(e) => {
		e.stopPropagation();
		onPointerDownNode(id, e);
	}}
	onpointerenter={() => (hovered = true)}
	onpointerleave={() => (hovered = false)}
>
	<!-- Node body -->
	<rect
		x={-WIDTH / 2}
		y={-HEIGHT / 2}
		width={WIDTH}
		height={HEIGHT}
		rx="6"
		ry="6"
		fill={fillColor}
		stroke={strokeColor}
		stroke-width={strokeWidth}
	/>

	<!-- Stage accent bar (left side) -->
	<rect
		x={-WIDTH / 2}
		y={-HEIGHT / 2}
		width="4"
		height={HEIGHT}
		rx="2"
		fill={STAGE_STROKE[stage] ?? '#8b5cf6'}
	/>

	<!-- Icon -->
	{#if iconClass}
		<foreignObject x={-WIDTH / 2 + 8} y={-8} width="16" height="16">
			<i class="{iconClass} text-[10px] text-gray-500"></i>
		</foreignObject>
	{/if}

	<!-- Label -->
	{#each lines as line, i}
		<text
			x={iconClass ? -WIDTH / 2 + 28 : 0}
			y={-((lines.length - 1) * 6) + i * 12 + 4}
			font-size="11"
			fill="#1e293b"
			text-anchor={iconClass ? 'start' : 'middle'}
			dominant-baseline="middle"
			class="select-none pointer-events-none"
		>
			{line}
		</text>
	{/each}

	<!-- Input handle (left) - only for non-KNOW stages -->
	{#if stage > 0}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<circle
			cx={-WIDTH / 2}
			cy={0}
			r={HANDLE_R}
			fill="white"
			stroke="#4D179A"
			stroke-width="1.5"
			class="cursor-crosshair"
			onpointerup={(e) => {
				e.stopPropagation();
				onPointerUpInput(id, e);
			}}
		/>
	{/if}

	<!-- Output handle (right) -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<circle
		cx={WIDTH / 2}
		cy={0}
		r={HANDLE_R}
		fill="white"
		stroke="#4D179A"
		stroke-width="1.5"
		class="cursor-crosshair"
		onpointerdown={(e) => {
			e.stopPropagation();
			onPointerDownOutput(id, e);
		}}
	/>

	<!-- Delete button (visible on hover/select) -->
	{#if selected || hovered}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<circle
			cx={WIDTH / 2 - 4}
			cy={-HEIGHT / 2 + 4}
			r="8"
			fill="#ef4444"
			class="cursor-pointer"
			onpointerdown={(e) => {
				e.stopPropagation();
				onDelete(id);
			}}
		/>
		<text
			x={WIDTH / 2 - 4}
			y={-HEIGHT / 2 + 5}
			font-size="10"
			fill="white"
			text-anchor="middle"
			dominant-baseline="middle"
			class="pointer-events-none select-none"
		>
			✕
		</text>
	{/if}
</g>
