<script lang="ts">
	import { isDark } from '#lib/utils/helpers.js';
	import { safeTranslate } from '#lib/utils/i18n.js';

	interface Props {
		name: string | null | undefined;
		hexcolor?: string | null;
		class?: string;
	}

	let { name, hexcolor, class: _class = '' }: Props = $props();

	// Colours come from the database and reach inline styles: only bare hex gets through.
	const HEX = /^#[0-9a-fA-F]{6}$/;
	let color = $derived(hexcolor && HEX.test(hexcolor) ? hexcolor : '');
</script>

{#if name}
	<span
		class="badge {color
			? isDark(color)
				? 'text-white'
				: 'text-surface-950'
			: 'bg-surface-100-900 text-surface-600-400'} {_class}"
		style={color ? `background-color: ${color}` : undefined}
	>
		{safeTranslate(name)}
	</span>
{/if}
