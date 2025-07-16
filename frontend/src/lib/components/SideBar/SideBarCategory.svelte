<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	interface Props {
		item: any; // Specify the type of 'item' as a key of 'Sidebar'
	}

	let { item }: Props = $props();
</script>

<span
	class="whitespace-nowrap text-primary-800 font-semibold uppercase tracking-tighter text-xs"
	data-testid={'accordion-item-' + item.name.toLowerCase().replace(' ', '-')}
>
	{safeTranslate(item.name)}
</span>
