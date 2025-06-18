<script lang="ts">
	interface Props {
		icon: any;
		text: any;
		count?: number;
	}

	let { icon, text, count = 0 }: Props = $props();
</script>

<div
	class="bg-white rounded-lg shadow-md p-4 min-h-20 flex items-center gap-4 transition-all hover:shadow-lg"
>
	<div class="text-5xl font-bold text-slate-800">{count}</div>
	<div class="flex flex-col items-end ml-auto">
		<div class="text-3xl text-slate-700 mb-1"><i class={icon}></i></div>
		<div class="text-slate-500 text-xs font-medium">{text}</div>
	</div>
</div>
