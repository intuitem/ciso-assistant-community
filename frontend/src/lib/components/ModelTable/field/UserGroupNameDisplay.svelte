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

	const MAX_VISIBLE = 4; // How many folder to show at once (including the first one) before shortening with "..."
	const LAST_VISIBLE = MAX_VISIBLE - 1; // How many of the last folders to show when shortening

	let fullPath = $state('');

	$effect(() => {
		const arr = [...meta.path.slice(0, -1).map((f) => f.str), cell.folder];
		const shortened = arr.length > MAX_VISIBLE ? [arr[0], '...', ...arr.slice(-LAST_VISIBLE)] : arr;
		fullPath = shortened.join(' / ');
	});
</script>

<span>{fullPath} - {safeTranslate(cell.role)}</span>
