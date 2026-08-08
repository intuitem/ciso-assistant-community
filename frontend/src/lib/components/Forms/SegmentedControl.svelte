<script lang="ts">
	/**
	 * Fresh, controlled segmented control (no superForm dependency).
	 * Reports the clicked option through `onChange`; the parent decides what to do
	 * (e.g. toggle back to a default when the active option is clicked again).
	 */
	interface Option {
		value: string;
		label: string;
	}
	interface Props {
		options: Option[];
		value?: string | null;
		onChange?: (value: string) => void;
		/** Per-value class applied to the selected segment (e.g. 'bg-green-300'). */
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

	const sizeClasses = $derived(size === 'sm' ? 'text-xs px-2.5 py-1' : 'text-sm px-3.5 py-1.5');
</script>

<div
	role="radiogroup"
	aria-label={ariaLabel}
	class="inline-flex flex-wrap items-center gap-0.5 rounded-lg border border-surface-300 bg-surface-100 p-0.5 {disabled
		? 'opacity-50 pointer-events-none'
		: ''} {className}"
>
	{#each options as option (option.value)}
		{@const selected = option.value === value}
		<button
			type="button"
			role="radio"
			aria-checked={selected}
			{disabled}
			onclick={() => onChange(option.value)}
			class="rounded-md font-medium whitespace-nowrap transition-colors {sizeClasses} {selected
				? (colorMap[option.value] ?? 'preset-filled-primary-500')
				: 'text-surface-600 hover:bg-surface-200'}"
		>
			{option.label}
		</button>
	{/each}
</div>
