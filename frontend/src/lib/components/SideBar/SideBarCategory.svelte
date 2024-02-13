<script lang="ts">
	export let item: any; // Specify the type of 'item' as a key of 'Sidebar'
	import * as m from '$paraglide/messages';

	const sidebar: any = {
		overview: m.overview(),
		context: m.context(),
		governance: m.governance(),
		risk: m.risk(),
		compliance: m.compliance(),
		organisation: m.organisation(),
		extra: m.extra(),
	}
</script>

<span class="whitespace-nowrap text-primary-800 font-semibold uppercase tracking-tighter text-xs">
	{sidebar[item.name]}
</span>
