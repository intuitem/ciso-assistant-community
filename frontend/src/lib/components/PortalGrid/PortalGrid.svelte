<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	let { sections = [], onTrigger }: { sections: any[]; onTrigger?: (item: any) => void } = $props();

	function handleKey(e: KeyboardEvent, item: any) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onTrigger?.(item);
		}
	}
</script>

<div class="space-y-10">
	{#each sections as section}
		<section>
			{#if section.title}
				<h2 class="mb-4 text-sm font-semibold uppercase tracking-wide text-surface-500">
					{section.title}
				</h2>
			{/if}
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each section.items ?? [] as item}
					{#if item.kind === 'metric'}
						<div
							class="flex flex-col justify-center rounded-2xl border border-surface-200-800 bg-surface-50-950 p-5 shadow-sm"
						>
							<div class="text-3xl font-bold text-surface-900-100">{item.target?.value ?? '—'}</div>
							<div class="mt-1 text-sm text-surface-600-400">{safeTranslate(item.title)}</div>
						</div>
					{:else if item.kind === 'badge'}
						<div
							class="flex flex-col items-center justify-center gap-3 rounded-2xl border border-surface-200-800 bg-surface-50-950 p-5 text-center shadow-sm"
						>
							{#if item.target?.image_url}
								<img src={item.target.image_url} alt={item.title} class="h-16 object-contain" />
							{:else}
								<i class="fa-solid {item.icon || 'fa-certificate'} text-4xl text-violet-500"></i>
							{/if}
							<div class="text-sm font-medium text-surface-800-200">
								{safeTranslate(item.title)}
							</div>
						</div>
					{:else}
						<div
							role="button"
							tabindex="0"
							onclick={() => onTrigger?.(item)}
							onkeydown={(e) => handleKey(e, item)}
							class="group flex items-start gap-4 rounded-2xl border border-surface-200-800 bg-surface-50-950 p-5 text-left shadow-sm transition-all hover:border-violet-400 hover:shadow-md cursor-pointer"
						>
							<div
								class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-violet-500 to-fuchsia-500 text-white transition-transform group-hover:scale-110"
							>
								<i class="fa-solid {item.icon || 'fa-star'} text-lg"></i>
							</div>
							<div class="min-w-0">
								<div class="font-semibold text-surface-800-200">{safeTranslate(item.title)}</div>
								{#if item.description}
									<div class="mt-0.5 text-xs text-surface-600-400">
										<MarkdownRenderer content={item.description} />
									</div>
								{/if}
							</div>
							{#if item.kind === 'external'}
								<i class="fa-solid fa-arrow-up-right-from-square ml-auto text-xs text-surface-400"
								></i>
							{:else if item.kind === 'document'}
								<i class="fa-solid fa-download ml-auto text-xs text-surface-400"></i>
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		</section>
	{/each}
</div>
