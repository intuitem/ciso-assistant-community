<script lang="ts">
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import { m } from '#paraglide/messages.js';

	interface LinkedScenario {
		id: string;
		str: string;
	}

	interface Props {
		meta: { risk_scenarios_outside_selection?: LinkedScenario[] };
		cell: LinkedScenario[] | null;
	}

	let { meta, cell }: Props = $props();

	const linked = $derived([...(cell ?? [])].sort((a, b) => a.str.localeCompare(b.str)));
	// Present only when the action plan is filtered by a scenario selection.
	const outside = $derived(meta?.risk_scenarios_outside_selection ?? []);
</script>

<div class="flex flex-col gap-1">
	{#if linked.length > 0}
		<!-- The table clips cells at 8em: cap the list so the hint below it stays visible. -->
		<ul
			class="list-disc pl-4 whitespace-normal {outside.length > 0
				? 'max-h-[4.5em] overflow-hidden hover:overflow-y-auto'
				: ''}"
		>
			{#each linked as scenario (scenario.id)}
				<li>
					<Anchor href="/risk-scenarios/{scenario.id}" class="anchor" stopPropagation
						>{scenario.str}</Anchor
					>
				</li>
			{/each}
		</ul>
	{/if}
	{#if outside.length > 0}
		<span
			class="text-xs text-surface-600-400 underline decoration-dotted underline-offset-2 w-fit cursor-help"
			title={outside.map((s) => s.str).join('\n')}
			data-testid="outside-selection-count"
		>
			{m.outsideSelectionCount({ count: outside.length })}
		</span>
	{/if}
</div>
