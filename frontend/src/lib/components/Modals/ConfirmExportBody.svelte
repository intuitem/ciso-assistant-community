<!-- ConfirmExportBody.svelte -->
<script>
	import * as m from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	export let types = [];
</script>

<div class="space-y-4">
	<div class="text-lg">
		{m.bodyModalExportFolder()}
		<div class="mt-2 flex flex-wrap gap-2">
			{#each types as type}
				<span class="badge variant-filled-warning">{safeTranslate(type)}</span>
			{/each}
		</div>
	</div>
</div>
