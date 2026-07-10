<script lang="ts">
	import { isDark } from '$lib/utils/helpers';

	interface Props {
		classification: { abbreviation?: string; hexcolor?: string; name?: string } | null | undefined;
		class?: string;
	}

	let { classification, class: klass = '' }: Props = $props();
</script>

{#if classification}
	{@const bg = classification.hexcolor || '#64748b'}
	<span
		class="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase leading-none ring-1 ring-black/10 {klass}"
		style="background:{bg}; color:{isDark(bg) ? '#ffffff' : '#0f172a'}"
		title={classification.name}
	>
		{classification.name || classification.abbreviation}
	</span>
{/if}
