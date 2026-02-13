<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	interface Folder {
		str: string;
		id: string;
	}
	interface Props {
		cell: { folder: string; role: string };
		meta: { path: Folder[] };
	}
	let { cell, meta }: Props = $props();

	let fullPath = $state('');

	$effect(() => {
		const arr = [...meta.path.slice(0, -1).map((f) => f.str), cell.folder];
		fullPath = arr.join(' / ');
	});
</script>

<span>{fullPath} - {safeTranslate(cell.role)}</span>
