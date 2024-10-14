<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';

	export let cell: { folder: string; role: string };
	export const meta: any = undefined;
</script>

<span>{cell.folder} - {safeTranslate(cell.role)}</span>
