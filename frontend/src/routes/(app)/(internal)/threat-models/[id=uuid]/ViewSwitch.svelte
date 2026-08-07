<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		threatModelId: string;
		active: 'select' | 'graph';
	}

	let { threatModelId, active }: Props = $props();

	const views = [
		{ key: 'select', href: 'select', icon: 'fa-table-cells', label: m.selectionView() },
		{ key: 'graph', href: 'graph', icon: 'fa-diagram-project', label: m.graphView() }
	] as const;
</script>

<div class="flex rounded-base border border-surface-300-700 overflow-hidden">
	{#each views as view (view.key)}
		<a
			href="/threat-models/{threatModelId}/{view.href}"
			aria-current={active === view.key ? 'page' : undefined}
			class="px-3 py-1.5 text-sm flex items-center gap-1.5 {active === view.key
				? 'preset-filled-primary-500'
				: 'hover:bg-surface-100-900 text-surface-700-300'}"
		>
			<i class="fa-solid {view.icon} text-xs"></i>
			{view.label}
		</a>
	{/each}
</div>
