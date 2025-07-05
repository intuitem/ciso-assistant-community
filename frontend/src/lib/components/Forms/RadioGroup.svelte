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
	<div
		class="p-1 inline-flex gap-1 grow flex-wrap items-center bg-gray-200 border border-gray-400 rounded-md {classes} {disabledClasses}"
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
							{disabled}
						/>
					</div>
					{option[labelKey]}
				</div>
			</label>
		{/each}
	</div>
	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}
</div>
