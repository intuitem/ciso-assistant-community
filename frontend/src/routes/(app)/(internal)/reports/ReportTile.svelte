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
			compliance: 'bg-surface-50-950 border-blue-300 hover:border-blue-400',
			risk: 'bg-surface-50-950 border-red-300 hover:border-red-400',
			governance: 'bg-surface-50-950 border-green-300 hover:border-green-400',
			operations: 'bg-surface-50-950 border-yellow-300 hover:border-yellow-400',
			assets: 'bg-surface-50-950 border-purple-300 hover:border-purple-400'
		};
		return colors[category] || 'bg-surface-50-950 border-surface-200-800 hover:border-surface-400-600';
	}

	function getCategoryIconColor(category: string): string {
		const colors: Record<string, string> = {
			compliance: 'text-blue-600',
			risk: 'text-red-600',
			governance: 'text-green-600',
			operations: 'text-yellow-600',
			assets: 'text-purple-600'
		};
		return colors[category] || 'text-surface-600-400';
	}

	const baseClasses =
		'block text-left p-6 rounded-lg border-2 transition-all duration-200 hover:shadow-lg transform hover:-translate-y-1 cursor-pointer';
</script>

{#if href}
	<a {href} class="{baseClasses} {getCategoryColor(category)}">
		<div class="flex items-start gap-4">
			<div class="flex-shrink-0">
				<div class="w-12 h-12 rounded-lg bg-surface-50-950 flex items-center justify-center shadow-sm">
					<i class="{icon} text-2xl {getCategoryIconColor(category)}"></i>
				</div>
			</div>
			<div class="flex-1 min-w-0 flex flex-col">
				<h3 class="text-lg font-semibold text-surface-950-50 mb-2">
					{title}
				</h3>
				<p class="text-sm text-surface-600-400 leading-relaxed mb-auto">
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
									class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-surface-100-900 text-surface-600-400 border border-surface-200-800"
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
				<div class="w-12 h-12 rounded-lg bg-surface-50-950 flex items-center justify-center shadow-sm">
					<i class="{icon} text-2xl {getCategoryIconColor(category)}"></i>
				</div>
			</div>
			<div class="flex-1 min-w-0 flex flex-col">
				<h3 class="text-lg font-semibold text-surface-950-50 mb-2">
					{title}
				</h3>
				<p class="text-sm text-surface-600-400 leading-relaxed mb-auto">
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
									class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-surface-100-900 text-surface-600-400 border border-surface-200-800"
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
