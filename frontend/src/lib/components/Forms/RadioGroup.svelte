<script lang="ts">
	interface Props {
		possibleOptions: { id: string; label: string }[];
		colorMap: { [key: string]: string };
		value: string | undefined;
		onChange: (value: string) => void;
		inputName: string;
	}
	let { possibleOptions, colorMap, value, onChange, inputName }: Props = $props();
</script>

<div class="p-1 flex gap-1 w-full flex-wrap items-center">
	{#each possibleOptions as option}
		{@const color = colorMap[option.id]}
		<label class="flex-auto rounded-lg {option.id === value ? color : ''}">
			<div class="text-base text-center cursor-pointer px-4 py-1 hover:variant-soft h-full">
				<div class="h-0 w-0 overflow-hidden">
					<input
						type="radio"
						name={inputName}
						class="invisible"
						id={option.id}
						onchange={() => {
							const newValue = value === option.id ? 'not_assessed' : option.id;
							onChange(newValue);
						}}
					/>
				</div>
				{option.label}
			</div>
		</label>
	{/each}
</div>
