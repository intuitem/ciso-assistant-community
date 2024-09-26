<script lang="ts">
	import { localItems, toCamelCase } from '$lib/utils/locales';

	export let cell: { folder: string; role: string };
	export const meta: any = undefined;
</script>

<span>{cell.folder} - {localItems()[toCamelCase(cell.role)]}</span>
