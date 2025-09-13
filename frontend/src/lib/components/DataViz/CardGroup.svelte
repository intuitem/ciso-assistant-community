<script lang="ts">
	interface Props {
		title: string;
		icon?: string;
		description?: string;
		children: import('svelte').Snippet;
	}

	let { title, icon = '', description = '', children }: Props = $props();
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
	<div class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-3">
		{@render children()}
	</div>
</div>
