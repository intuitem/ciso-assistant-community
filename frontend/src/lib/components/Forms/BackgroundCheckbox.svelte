<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import { fade } from 'svelte/transition';

	interface Props {
		label?: string;
		field: string;
		valuePath?: any;
		helpText?: string;
		cachedValue?: boolean;
		form: SuperForm<Record<string, boolean | undefined>>;
		hidden?: boolean;
		disabled?: boolean;
		classes?: string;
		classesContainer?: string;
		onChange?: (value: boolean) => void;
		[key: string]: any;
	}

	let {
		label,
		field,
		valuePath = field,
		helpText,
		cachedValue,
		form,
		hidden = false,
		disabled = false,
		classes = '',
		classesContainer = '',
		onChange = () => {},
		...rest
	}: Props = $props();

	label = label ?? field;

	const { value, errors } = formFieldProxy(form, valuePath);
	$effect(() => {
		cachedValue = $value;
	});

	function toggle() {
		if (!disabled) {
			$value = !$value;
			onChange($value);
		}
	}

	let classesHidden = $derived((h: boolean) => (h ? 'hidden' : ''));
	let classesDisabled = $derived((d: boolean) =>
		d ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
	);
</script>

<div class="{classesContainer} {classesHidden(hidden)}">
	<div
		class="flex flex-col p-4 border rounded-lg transition-all duration-300 ease-in-out
		       min-h-[150px]

		       {classesDisabled(disabled)} {classes}
		       {$value
			? 'bg-gradient-to-br from-primary-400 to-primary-500 border-primary text-white'
			: 'bg-white border-gray-300'}"
		onclick={toggle}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				toggle();
			}
		}}
		role="checkbox"
		aria-checked={$value}
		tabindex="0"
	>
		<div class="flex justify-between items-center min-h-[2.5rem]">
			<span class="font-semibold">{label}</span>

			{#if $value}
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
				{$value ? 'text-primary-100' : 'text-gray-500'}"
			>
				{helpText}
			</p>
		{/if}
	</div>

	{#if $errors?.length}
		<div class="mt-1">
			{#each $errors as error}
				<p class="text-red-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
</div>
