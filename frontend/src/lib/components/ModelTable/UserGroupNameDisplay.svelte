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

	const fullPath = [...meta.path.slice(0, -1).map((folder) => folder.str), cell.folder].join('/');
</script>

<span>{fullPath} - {safeTranslate(cell.role)}</span>
