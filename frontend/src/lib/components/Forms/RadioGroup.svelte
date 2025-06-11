<script lang="ts">
	import internal from 'stream';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	interface Props {
		possibleOptions: { id: string; label: string }[];
		colorMap?: { [key: string]: string };
		form?: SuperForm<Record<string, any>>;
		initialValue?: any;
		onChange?: (value: string) => void;
		field: string;
		key: string;
		labelKey: string;
	}
	let {
		possibleOptions,
		colorMap = {},
		form,
		initialValue,
		onChange = () => {},
		field,
		key,
		labelKey
	}: Props = $props();

	const { value } = form ? formFieldProxy(form, field) : {};

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
</script>

<div
	class="p-1 flex gap-1 w-full flex-wrap items-center bg-gray-200 border border-gray-400 rounded-md"
>
	{#each possibleOptions as option}
		{@const color = colorMap[option.id] ?? 'preset-filled-primary-500'}
		<label class="flex-auto rounded-lg {option[key] === internalValue ? color : ''}">
			<div class="text-base text-center cursor-pointer px-4 py-1 hover:variant-soft h-full">
				<div class="h-0 w-0 overflow-hidden">
					<input
						type="radio"
						name={field}
						class="invisible"
						id={option.id}
						onchange={() => {
							internalValue = option[key];
							onChange(internalValue);
						}}
					/>
				</div>
				{option[labelKey]}
			</div>
		</label>
	{/each}
</div>
