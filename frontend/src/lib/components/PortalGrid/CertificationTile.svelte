<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	let { item, onTrigger }: { item: any; onTrigger?: (item: any) => void } = $props();

	const target = $derived(item.target ?? {});
	const clickable = $derived(!!(target.url || target.token));

	function fmt(d: string) {
		const date = new Date(d);
		return isNaN(date.getTime())
			? d
			: date.toLocaleDateString(undefined, { year: 'numeric', month: 'short' });
	}

	const expired = $derived(target.valid_until && new Date(target.valid_until) < new Date());

	const validity = $derived.by(() => {
		if (target.valid_from && target.valid_until)
			return `${fmt(target.valid_from)} – ${fmt(target.valid_until)}`;
		if (target.valid_until) return `${m.validUntil()} ${fmt(target.valid_until)}`;
		if (target.valid_from) return `${m.since()} ${fmt(target.valid_from)}`;
		return '';
	});

	function handleKey(e: KeyboardEvent) {
		if (clickable && (e.key === 'Enter' || e.key === ' ')) {
			e.preventDefault();
			onTrigger?.(item);
		}
	}
</script>

<div
	role={clickable ? 'button' : undefined}
	tabindex={clickable ? 0 : undefined}
	onclick={clickable ? () => onTrigger?.(item) : undefined}
	onkeydown={clickable ? handleKey : undefined}
	class="flex flex-col items-center justify-center gap-2 rounded-2xl border border-surface-200-800 bg-surface-50-950 p-5 text-center shadow-sm {clickable
		? 'cursor-pointer transition-all hover:border-violet-400 hover:shadow-md'
		: ''}"
>
	{#if target.image_url}
		<img src={target.image_url} alt={item.title} class="h-16 object-contain" />
	{:else}
		<i class="fa-solid {item.icon || 'fa-certificate'} text-4xl text-violet-500"></i>
	{/if}
	<div class="text-sm font-medium text-surface-800-200">{safeTranslate(item.title)}</div>
	{#if validity}
		<div class="text-xs {expired ? 'text-error-600' : 'text-surface-500'}">
			{validity}
		</div>
	{/if}
	{#if expired}
		<span class="rounded-full bg-error-500/15 px-2 py-0.5 text-[10px] uppercase text-error-700">
			{m.expired()}
		</span>
	{/if}
	{#if target.token}
		<i class="fa-solid fa-download text-xs text-surface-400"></i>
	{/if}
</div>
