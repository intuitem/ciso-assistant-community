<script lang="ts">
	export let icon;
	export let text;
	export let count = 0;
</script>

<div class="bg-white rounded-lg p-2 min-h-20 flex">
	<div class="text-3xl font-semibold">{count}</div>
	<div>
		<div class="text-3xl text-slate-700"><i class={icon}></i></div>
		<div class="text-slate-500 text-xs">{text}</div>
	</div>
</div>
