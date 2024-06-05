<script lang="ts">
	export let item: any; // Specify the type of 'item' as a key of 'Sidebar'
	import { localItems } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';
</script>

<span class="whitespace-nowrap text-primary-800 font-semibold uppercase tracking-tighter text-xs">
	{localItems()[item.name]}
</span>
