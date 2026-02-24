<script lang="ts">
	interface Props {
		id: string;
		x: number;
		y: number;
		operator: 'AND' | 'OR';
		onToggle: (id: string) => void;
	}

	let { id, x, y, operator, onToggle }: Props = $props();

	const SIZE = 36;
	let hovered = $state(false);

	const fillColor = $derived(hovered ? '#f3e8ff' : '#ffffff');
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<g
	transform="translate({x}, {y})"
	class="logic-gate-node cursor-pointer"
	onpointerenter={() => (hovered = true)}
	onpointerleave={() => (hovered = false)}
	onpointerdown={(e) => {
		e.stopPropagation();
		onToggle(id);
	}}
>
	<circle
		cx={0}
		cy={0}
		r={SIZE / 2}
		fill={fillColor}
		stroke="#4D179A"
		stroke-width="1.5"
	/>
	<text
		x={0}
		y={1}
		font-size="11"
		font-weight="700"
		fill="#4D179A"
		text-anchor="middle"
		dominant-baseline="middle"
		class="select-none pointer-events-none"
	>
		{operator}
	</text>
</g>
