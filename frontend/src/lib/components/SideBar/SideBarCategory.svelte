<script lang="ts">
	export let item: any; // Specify the type of 'item' as a key of 'Sidebar'
	import * as m from '$paraglide/messages.js';
</script>

<span class="whitespace-nowrap text-primary-800 font-semibold uppercase tracking-tighter text-xs">
	{m[item.name]()}
</span>
