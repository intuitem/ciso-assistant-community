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

	let fullPathArray = [...meta.path.slice(0, -1).map((folder) => folder.str), cell.folder];

	const MAX_VISIBLE = 4; // How many folder to show at once (including the first one) before shortening with "..."
	const LAST_VISIBLE = MAX_VISIBLE - 1; // How many of the last folders to show when shortening

	const shortenedPath =
		fullPathArray.length > MAX_VISIBLE
			? [fullPathArray[0], '...', ...fullPathArray.slice(-LAST_VISIBLE)]
			: fullPathArray;
	const fullPath = shortenedPath.join(' / ');
</script>

<span>{fullPath} - {safeTranslate(cell.role)}</span>
