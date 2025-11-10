<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		title: string;
		description: string;
		icon: string;
		category: string;
		onclick?: () => void;
		href?: string;
		tags?: string[];
	}

	let { title, description, icon, category, onclick, href, tags = [] }: Props = $props();

	function getCategoryColor(category: string): string {
		const colors: Record<string, string> = {
			compliance: 'bg-blue-50 border-blue-200 hover:border-blue-400',
			risk: 'bg-red-50 border-red-200 hover:border-red-400',
			governance: 'bg-green-50 border-green-200 hover:border-green-400',
			operations: 'bg-yellow-50 border-yellow-200 hover:border-yellow-400',
			assets: 'bg-purple-50 border-purple-200 hover:border-purple-400'
		};
		return colors[category] || 'bg-gray-50 border-gray-200 hover:border-gray-400';
	}

	function getCategoryIconColor(category: string): string {
		const colors: Record<string, string> = {
			compliance: 'text-blue-600',
			risk: 'text-red-600',
			governance: 'text-green-600',
			operations: 'text-yellow-600',
			assets: 'text-purple-600'
		};
		return colors[category] || 'text-gray-600';
	}

	const baseClasses =
		'block text-left p-6 rounded-lg border-2 transition-all duration-200 hover:shadow-lg transform hover:-translate-y-1 cursor-pointer';
</script>

{#if href}
	<a {href} class="{baseClasses} {getCategoryColor(category)}">
		<div class="flex items-start gap-4">
			<div class="flex-shrink-0">
				<div class="w-12 h-12 rounded-lg bg-white flex items-center justify-center shadow-sm">
					<i class="{icon} text-2xl {getCategoryIconColor(category)}"></i>
				</div>
			</div>
			<div class="flex-1 min-w-0 flex flex-col">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">
					{title}
				</h3>
				<p class="text-sm text-gray-600 leading-relaxed mb-auto">
					{description}
				</p>
				<div class="mt-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center text-sm font-medium {getCategoryIconColor(category)}">
							{m.generateReport ? m.generateReport() : 'Generate Report'}
							<i class="fas fa-arrow-right ml-2 text-xs"></i>
						</div>
					</div>
					{#if tags.length > 0}
						<div class="flex flex-wrap gap-1 mt-3">
							{#each tags as tag}
								<span
									class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200"
								>
									{tag}
								</span>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</a>
{:else}
	<button type="button" class="{baseClasses} {getCategoryColor(category)}" {onclick}>
		<div class="flex items-start gap-4">
			<div class="flex-shrink-0">
				<div class="w-12 h-12 rounded-lg bg-white flex items-center justify-center shadow-sm">
					<i class="{icon} text-2xl {getCategoryIconColor(category)}"></i>
				</div>
			</div>
			<div class="flex-1 min-w-0 flex flex-col">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">
					{title}
				</h3>
				<p class="text-sm text-gray-600 leading-relaxed mb-auto">
					{description}
				</p>
				<div class="mt-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center text-sm font-medium {getCategoryIconColor(category)}">
							{m.generateReport ? m.generateReport() : 'Generate Report'}
							<i class="fas fa-arrow-right ml-2 text-xs"></i>
						</div>
					</div>
					{#if tags.length > 0}
						<div class="flex flex-wrap gap-1 mt-3">
							{#each tags as tag}
								<span
									class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200"
								>
									{tag}
								</span>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</button>
{/if}
