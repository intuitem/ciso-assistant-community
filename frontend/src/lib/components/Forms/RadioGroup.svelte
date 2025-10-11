<script lang="ts">
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import type { CacheLock } from '$lib/utils/types';

	interface Props {
		possibleOptions: { id: string; label: string }[];
		classes?: string;
		colorMap?: { [key: string]: string };
		label?: string;
		helpText?: string;
		form?: SuperForm<Record<string, any>>;
		disabled?: boolean;
		initialValue?: any;
		nullable?: boolean;
		onChange?: (value: string) => void;
		cacheLock?: CacheLock;
		cachedValue?: any;
		field: string;
		valuePath?: string;
		key: string;
		labelKey: string;
	}
	let {
		possibleOptions,
		classes = '',
		colorMap = {},
		label,
		helpText,
		form,
		disabled = false,
		initialValue,
		nullable = false,
		onChange = () => {},
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x) => x
		},
		cachedValue = $bindable(),
		field,
		valuePath = field,
		key = 'value',
		labelKey = 'label'
	}: Props = $props();

	const { value } = form ? formFieldProxy(form, valuePath) : {};

	let internalValue = $state(value ? $value : initialValue);

	$effect(() => {
		if (initialValue) {
			internalValue = initialValue;
		}
	});

	$effect(() => {
		if (value) {
			$value = internalValue;
		}
	});

	$effect(() => {
		cacheLock.promise.then((cacheResult) => {
			if (cacheResult) $value = cacheResult;
		});
	});

	$effect(() => (cachedValue = $value));

	let disabledClasses = $derived(disabled ? 'opacity-50 cursor-not-allowed' : '');
	let cursorClass = $derived(disabled ? 'cursor-inherit' : 'cursor-pointer');
	let labeledOptions = $derived(possibleOptions.filter((option) => option[labelKey]));
	let radioInputs: { [key: string]: HTMLInputElement } = {};
</script>

<div class="control overflow-x-clip grow">
	{#if label}
		<label class="text-sm font-semibold" for={field}>{label}</label><br />
	{/if}
	<div
		class="p-1 inline-flex gap-1 grow flex-wrap items-center bg-gray-200 border border-gray-400 rounded-md {classes} {disabledClasses}"
	>
		{#each labeledOptions as option}
			{@const color = colorMap[option.id] ?? 'preset-filled-primary-500'}
			<button
				class="cursor-[inherit] flex-auto rounded-lg {option[key] === internalValue ? color : ''}"
				onclick={(event) => {
					event.preventDefault();
					if (disabled) return;
					if (internalValue === option[key]) {
						if (nullable) {
							internalValue = null;
							onChange(internalValue);
							return;
						}
						return;
					}
					value?.set(option[key]);
					internalValue = option[key];
					onChange(internalValue);
				}}
			>
				<div class="text-base text-center px-4 py-1 {cursorClass} hover:preset-tonal h-full">
					{option[labelKey]}
				</div>
			</button>
		{/each}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
