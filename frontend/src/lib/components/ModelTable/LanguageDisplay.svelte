<script lang="ts">
	import { LOCALE_DISPLAY_MAP } from '$lib/utils/constants.js';
	export let cell: keyof typeof LOCALE_DISPLAY_MAP;
	export const meta: any = undefined;
	$: display = LOCALE_DISPLAY_MAP[cell];
</script>

<span {...$$restProps}>{display}</span>
