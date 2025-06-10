<script lang="ts">
	interface Props {
		possibleOptions: { id: string; label: string }[];
		colorMap?: { [key: string]: string };
		value: string | undefined;
		onChange: (value: string) => void;
		inputName: string;
		key: string;
		labelKey: string;
	}
	let {
		possibleOptions,
		colorMap = {},
		value,
		onChange,
		inputName,
		key,
		labelKey
	}: Props = $props();
</script>

<div
	class="p-1 flex gap-1 w-full flex-wrap items-center bg-gray-200 border border-gray-400 rounded-md"
>
	{#each possibleOptions as option}
		{@const color = colorMap[option.id] ?? 'preset-filled-primary-500'}
		<label class="flex-auto rounded-lg {option[key] === value ? color : ''}">
			<div class="text-base text-center cursor-pointer px-4 py-1 hover:variant-soft h-full">
				<div class="h-0 w-0 overflow-hidden">
					<input
						type="radio"
						name={inputName}
						class="invisible"
						id={option.id}
						onchange={() => onChange(option[key])}
					/>
				</div>
				{option[labelKey]}
			</div>
		</label>
	{/each}
</div>
