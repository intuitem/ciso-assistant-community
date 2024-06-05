<script lang="ts">
	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let cell: { folder: string; role: string };
	export const meta: any = undefined;
</script>

<span>{cell.folder} - {localItems()[toCamelCase(cell.role)]}</span>
