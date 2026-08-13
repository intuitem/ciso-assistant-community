<script lang="ts">
	/**
	 * Fresh, controlled segmented control (no superForm dependency).
	 * Inactive options stay neutral; hovering washes them with a soft tint of the
	 * option color, and the selected one fills with that color. `colorMap` maps a
	 * value to a hex color.
	 */
	interface Option {
		value: string;
		label: string;
	}
	interface Props {
		options: Option[];
		value?: string | null;
		onChange?: (value: string) => void;
		/** Per-value hex color used for the hover wash and the selected fill. */
		colorMap?: Record<string, string>;
		disabled?: boolean;
		size?: 'sm' | 'md';
		ariaLabel?: string;
		class?: string;
	}
	let {
		options,
		value = null,
		onChange = () => {},
		colorMap = {},
		disabled = false,
		size = 'md',
		ariaLabel,
		class: className = ''
	}: Props = $props();

	const sizeClasses = $derived(size === 'sm' ? 'text-xs px-3 py-1' : 'text-sm px-3.5 py-1.5');

	let hovered = $state<string | null>(null);

	function rgb(hex: string): [number, number, number] {
		const c = (hex ?? '').replace('#', '');
		return [parseInt(c.slice(0, 2), 16), parseInt(c.slice(2, 4), 16), parseInt(c.slice(4, 6), 16)];
	}
	// Mix a hex toward target; amount = target weight
	function mix(hex: string, target: [number, number, number], amount: number): string {
		const [r, g, b] = rgb(hex);
		const m = (a: number, t: number) => Math.round(a * (1 - amount) + t * amount);
		return `rgb(${m(r, target[0])} ${m(g, target[1])} ${m(b, target[2])})`;
	}
	// Filled-segment label color
	function selectedFg(hex: string): string {
		const [r, g, b] = rgb(hex);
		const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
		return luminance < 0.45 ? '#ffffff' : mix(hex, [0, 0, 0], 0.58);
	}
</script>

<div
	role="radiogroup"
	aria-label={ariaLabel}
	class="inline-flex flex-wrap items-center gap-1 rounded-lg bg-surface-100 p-1 ring-1 ring-surface-200/80 {disabled
		? 'opacity-50 pointer-events-none'
		: ''} {className}"
>
	{#each options as option (option.value)}
		{@const selected = option.value === value}
		{@const tint = colorMap[option.value] ?? '#94a3b8'}
		{@const hover = hovered === option.value && !selected}
		<button
			type="button"
			role="radio"
			aria-checked={selected}
			{disabled}
			onclick={() => onChange(option.value)}
			onpointerenter={() => (hovered = option.value)}
			onpointerleave={() => (hovered = null)}
			style:background-color={selected
				? tint
				: hover
					? mix(tint, [255, 255, 255], 0.82)
					: undefined}
			style:color={selected ? selectedFg(tint) : hover ? mix(tint, [0, 0, 0], 0.55) : undefined}
			class="rounded-md font-medium whitespace-nowrap transition-colors duration-150 {sizeClasses} {selected
				? 'shadow-sm'
				: 'text-surface-500'}"
		>
			{option.label}
		</button>
	{/each}
</div>
