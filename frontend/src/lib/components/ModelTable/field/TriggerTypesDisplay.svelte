<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		cell: string[] | null;
	}

	let { cell }: Props = $props();

	const ICONS: Record<string, string> = {
		manual: 'fa-hand-pointer',
		webhook: 'fa-tower-broadcast',
		schedule: 'fa-clock',
		internal_event: 'fa-bolt'
	};
	// Reuse the builder's trigger labels (internal_event -> triggerInternalEvent)
	const key = (type: string) =>
		'trigger' + type.replace(/(?:^|_)([a-z])/g, (_, c: string) => c.toUpperCase());
</script>

<div class="flex flex-wrap gap-1">
	{#each cell ?? [] as type}
		<span
			class="badge preset-tonal-surface text-xs whitespace-nowrap"
			data-testid="trigger-type-badge"
		>
			<i class="fa-solid {ICONS[type] ?? 'fa-bolt'} mr-1 opacity-60"></i>{safeTranslate(key(type))}
		</span>
	{:else}
		<span class="text-surface-400 text-xs">--</span>
	{/each}
</div>
