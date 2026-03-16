<script lang="ts">
	interface Props {
		currentType: string;
		onselect: (type: string) => void;
	}

	let { currentType, onselect }: Props = $props();
	let open = $state(false);

	const types = [
		{ value: 'text', label: 'Text', icon: 'fa-font', color: 'text-blue-600 bg-blue-50' },
		{
			value: 'number',
			label: 'Number',
			icon: 'fa-hashtag',
			color: 'text-emerald-600 bg-emerald-50'
		},
		{
			value: 'boolean',
			label: 'Boolean',
			icon: 'fa-toggle-on',
			color: 'text-green-600 bg-green-50'
		},
		{
			value: 'unique_choice',
			label: 'Single Choice',
			icon: 'fa-circle-dot',
			color: 'text-violet-600 bg-violet-50'
		},
		{
			value: 'multiple_choice',
			label: 'Multiple Choice',
			icon: 'fa-square-check',
			color: 'text-purple-600 bg-purple-50'
		},
		{ value: 'date', label: 'Date', icon: 'fa-calendar', color: 'text-amber-600 bg-amber-50' }
	];

	const currentTypeInfo = $derived(types.find((t) => t.value === currentType) ?? types[0]);

	function select(type: string) {
		onselect(type);
		open = false;
	}
</script>

<div class="relative">
	<button
		type="button"
		class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium {currentTypeInfo.color} hover:opacity-80 transition-opacity"
		onclick={() => (open = !open)}
	>
		<i class="fa-solid {currentTypeInfo.icon}"></i>
		{currentTypeInfo.label}
		<i class="fa-solid fa-chevron-down text-[10px] opacity-60"></i>
	</button>

	{#if open}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="fixed inset-0 z-20"
			onclick={() => (open = false)}
			onkeydown={(e) => e.key === 'Escape' && (open = false)}
		></div>
		<div
			class="absolute top-full left-0 mt-1 z-30 bg-white rounded-lg shadow-lg border border-gray-200 p-2 grid grid-cols-2 gap-1 w-56"
		>
			{#each types as type (type.value)}
				<button
					type="button"
					class="flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-gray-50 transition-colors {currentType ===
					type.value
						? 'ring-2 ring-blue-500 ring-offset-1'
						: ''}"
					onclick={() => select(type.value)}
				>
					<span class="w-7 h-7 rounded flex items-center justify-center {type.color}">
						<i class="fa-solid {type.icon} text-xs"></i>
					</span>
					<span class="text-gray-700 font-medium">{type.label}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>
