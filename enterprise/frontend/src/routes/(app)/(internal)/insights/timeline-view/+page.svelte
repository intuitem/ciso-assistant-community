<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import MyGantt from '$lib/components/GanttView/MyGantt.svelte';
	const tasks = data.data;
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	const lang = getLocale();
</script>

<main class="w-full p-2 items-center justify-center">
	<div class="text-sm italic text-slate-600">{m.planningTip()}</div>
	<div class="shadow"><MyGantt {tasks} {lang} /></div>
</main>
