<script lang="ts">
	interface Props {
		title: string;
		icon?: string;
		description?: string;
		maxColumns?: 2 | 3 | 4;
		children: import('svelte').Snippet;
	}

	let { title, icon = '', description = '', maxColumns = 4, children }: Props = $props();

	// Generate responsive grid classes based on maxColumns
	const gridClasses = $derived(() => {
		switch (maxColumns) {
			case 2:
				return 'grid grid-cols-1 sm:grid-cols-2 gap-3';
			case 3:
				return 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3';
			case 4:
			default:
				return 'grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-3';
		}
	});
</script>

<div class="space-y-3">
	<!-- Group Header -->
	<div class="flex items-center gap-3 pb-2 border-b border-gray-200">
		{#if icon}
			<div class="text-xl text-violet-600">
				<i class={icon}></i>
			</div>
		{/if}
		<div>
			<h3 class="text-lg font-semibold text-gray-800">{title}</h3>
			{#if description}
				<p class="text-sm text-gray-600">{description}</p>
			{/if}
		</div>
	</div>

	<!-- Cards Grid -->
	<div class={gridClasses()}>
		{@render children()}
	</div>
</div>
