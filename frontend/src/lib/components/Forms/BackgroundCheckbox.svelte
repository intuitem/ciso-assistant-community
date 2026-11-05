<script lang="ts" module>
	export type CheckboxAccent = 'primary' | 'tertiary';

	// Literal strings: Tailwind scans the source, so `from-${accent}-400` would
	// never be emitted.
	const ACCENT_CLASSES: Record<CheckboxAccent, { checked: string; helpText: string }> = {
		primary: {
			checked: 'bg-gradient-to-br from-primary-400 to-primary-500 border-primary text-white',
			helpText: 'text-primary-100'
		},
		tertiary: {
			checked: 'bg-gradient-to-br from-tertiary-400 to-tertiary-500 border-tertiary text-white',
			helpText: 'text-tertiary-100'
		}
	};
</script>

<script lang="ts">
	import { fade } from 'svelte/transition';

	interface Props {
		label?: string;
		field: string;
		/** Controlled — the caller owns the value, wherever it lives. */
		checked: boolean;
		onToggle: (next: boolean) => void;
		helpText?: string;
		/** Hover hint, chiefly why a disabled tile cannot be toggled. Rendered as
		 * `title`, which `aria-label` leaves free to be the description. */
		tooltip?: string;
		hidden?: boolean;
		disabled?: boolean;
		/** Supplied by the caller, which owns the form — the backend maps field
		 * errors back onto it via `handleErrorResponse`. */
		errors?: string[];
		/** `primary` for an instance setting, `tertiary` for the viewer's own. */
		accent?: CheckboxAccent;
		classes?: string;
		classesContainer?: string;
	}

	let {
		label,
		field,
		checked,
		onToggle,
		helpText,
		tooltip,
		hidden = false,
		disabled = false,
		errors = [],
		accent = 'primary',
		classes = '',
		classesContainer = ''
	}: Props = $props();

	const displayLabel = $derived(label ?? field);

	function toggle() {
		if (!disabled) onToggle(!checked);
	}
</script>

<div class="{classesContainer} {hidden ? 'hidden' : ''}">
	<div
		class="flex flex-col p-4 border rounded-lg transition-all duration-300 ease-in-out
		       min-h-[150px]

		       {disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} {classes}
		       {checked ? ACCENT_CLASSES[accent].checked : 'bg-surface-50-950 border-surface-300-700'}"
		onclick={toggle}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				toggle();
			}
		}}
		role="checkbox"
		aria-checked={checked}
		aria-disabled={disabled}
		aria-label={displayLabel}
		title={tooltip}
		tabindex="0"
	>
		<div class="flex justify-between items-center min-h-[2.5rem]">
			<span class="font-semibold">{displayLabel}</span>

			{#if checked}
				<span
					class="w-6 h-6 flex items-center justify-center"
					in:fade={{ duration: 200 }}
					out:fade={{ duration: 200 }}
				>
					<!-- SVG check stylisé -->
					<svg
						class="w-6 h-6 text-white"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="3"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M5 13l4 4L19 7" />
					</svg>
				</span>
			{/if}
		</div>

		{#if helpText}
			<p
				class="text-sm mt-1 transition-colors duration-300 ease-in-out
				{checked ? ACCENT_CLASSES[accent].helpText : 'text-surface-600-400'}"
			>
				{helpText}
			</p>
		{/if}
	</div>

	{#if errors.length}
		<div class="mt-1">
			{#each errors as error (error)}
				<p class="text-red-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
</div>
