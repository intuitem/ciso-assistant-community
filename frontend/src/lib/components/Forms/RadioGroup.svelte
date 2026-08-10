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

	const { value, errors } = form ? formFieldProxy(form, valuePath) : {};

	let internalValue = $state(value ? $value : initialValue);
	let lastExternalValue = $state(value ? $value : undefined);

	$effect(() => {
		if (initialValue) {
			internalValue = initialValue;
		}
	});

	// React to external changes to $value (avoid circular updates)
	$effect(() => {
		if (value && $value !== undefined && $value !== lastExternalValue) {
			lastExternalValue = $value;
			internalValue = $value;
		}
	});

	// Sync internalValue back to form and update radio button state
	$effect(() => {
		if (value && internalValue !== lastExternalValue) {
			$value = internalValue;
			lastExternalValue = internalValue;
		}
		const input = radioInputs[internalValue];
		if (input) input.checked = true;
	});

	$effect(() => {
		cacheLock.promise.then((cacheResult) => {
			if (cacheResult) $value = cacheResult;
		});
	});

	$effect(() => (cachedValue = $value));

	let disabledClasses = $derived(disabled ? 'opacity-50 cursor-not-allowed' : '');
	let labeledOptions = $derived(possibleOptions.filter((option) => option[labelKey]));
	let radioInputs: { [key: string]: HTMLInputElement } = {};
</script>

<div class="control overflow-x-clip grow">
	{#if label}
		<label class="text-sm font-semibold" for={field}>{label}</label><br />
	{/if}
	{#if $errors}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs font-medium">{error}</p>
			{/each}
		</div>
	{/if}
	<div
		class="p-1 inline-flex gap-1 grow flex-wrap items-center bg-surface-200-800 border border-surface-400-600 rounded-md {classes} {disabledClasses}"
	>
		{#each labeledOptions as option}
			{@const color = colorMap[option.id] ?? 'preset-filled-primary-500'}
			<label class="flex-auto rounded-lg {option[key] === internalValue ? color : ''}">
				<div class="text-base text-center cursor-pointer px-4 py-1 hover:preset-tonal h-full">
					<div class="h-0 w-0 overflow-hidden">
						<input
							type="radio"
							name={field}
							class="invisible"
							id={option.id}
							bind:this={radioInputs[option[key]]}
							onchange={(e) => {
								internalValue = option[key];
								onChange(internalValue);
							}}
							value={option[key]}
							{disabled}
						/>
					</div>
					{option[labelKey]}
				</div>
			</label>
		{/each}
	</div>
	{#if helpText}
		<p class="text-sm text-surface-600-400">{helpText}</p>
	{/if}
</div>
