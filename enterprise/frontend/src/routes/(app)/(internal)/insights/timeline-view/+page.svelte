<script lang="ts">
	import type { PageData } from './$types';
	import MyGantt from '$lib/components/GanttView/MyGantt.svelte';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const lang = getLocale();
	const tasks = data.data;
</script>

<main class="w-full p-2 items-center justify-center">
	<div class="text-sm italic text-slate-600">{m.planningTip()}</div>
	<div class="shadow"><MyGantt {tasks} {lang} /></div>
</main>
