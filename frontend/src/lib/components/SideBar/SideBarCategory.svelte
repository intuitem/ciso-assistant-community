<script lang="ts">
	export let item: any; // Specify the type of 'item' as a key of 'Sidebar'
	import { safeTranslate } from '$lib/utils/i18n';
</script>

<span class="whitespace-nowrap text-primary-800 font-semibold uppercase tracking-tighter text-xs">
	{safeTranslate(item.name)}
</span>
