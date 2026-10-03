<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Props {
		classification:
			{ name?: string; label?: string; str?: string; hexcolor?: string } | null | undefined;
		class?: string;
	}

	let { classification, class: _class = '' }: Props = $props();
</script>

{#if classification}
	<span
		class="badge border-2 font-bold uppercase {_class}"
		style="border-color: {classification.hexcolor ||
			'currentColor'}; color: {classification.hexcolor || 'inherit'}"
		title={m.classification()}
	>
		{classification.name ?? classification.label ?? classification.str}
	</span>
{/if}
