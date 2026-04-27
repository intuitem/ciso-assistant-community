<script lang="ts">
	import type { ConflictStrategy } from './types';

	interface Option {
		value: ConflictStrategy;
		label: string;
		desc: string;
		icon: string;
	}

	interface Props {
		strategy: ConflictStrategy;
		options?: Option[];
		disabled?: boolean;
	}

	const defaultOptions: Option[] = [
		{
			value: 'skip',
			label: 'Skip',
			desc: 'Leave the existing evidence untouched.',
			icon: 'fa-forward'
		},
		{
			value: 'add_revision',
			label: 'Add revision',
			desc: 'Keep the existing evidence; attach the new file as a new version.',
			icon: 'fa-code-branch'
		},
		{
			value: 'replace',
			label: 'Replace',
			desc: "Overwrite the latest revision's file. Keeps the evidence ID and links.",
			icon: 'fa-rotate'
		},
		{
			value: 'rename',
			label: 'Rename',
			desc: 'Append " (1)", " (2)" etc. so the new evidence coexists with the old one.',
			icon: 'fa-pen'
		}
	];

	let {
		strategy = $bindable('skip'),
		options = defaultOptions,
		disabled = false
	}: Props = $props();
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
	{#each options as opt}
		<label
			class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer
				{strategy === opt.value
				? 'border-indigo-500 bg-indigo-50'
				: 'border-gray-200 hover:border-gray-300'}
				{disabled ? 'opacity-50 cursor-not-allowed' : ''}"
		>
			<input
				type="radio"
				name="conflict_strategy"
				value={opt.value}
				bind:group={strategy}
				{disabled}
				class="mt-1"
			/>
			<div class="flex-1">
				<div class="font-medium text-sm">
					<i class="fa-solid {opt.icon} mr-1.5 text-gray-600"></i>{opt.label}
				</div>
				<div class="text-xs text-gray-600 mt-0.5">{opt.desc}</div>
			</div>
		</label>
	{/each}
</div>
