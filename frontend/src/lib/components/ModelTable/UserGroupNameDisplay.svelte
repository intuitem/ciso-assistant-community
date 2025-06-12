<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		cell: { folder: string; role: string };
	}

	let { cell }: Props = $props();
	export const meta: any = undefined;
</script>

<span>{cell.folder} - {safeTranslate(cell.role)}</span>
