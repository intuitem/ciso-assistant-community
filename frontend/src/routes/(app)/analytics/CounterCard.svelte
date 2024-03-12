<script lang="ts">
	export let count = 0;
	export let label: string;
	export let faIcon = '';
	export let iconColor = '';
</script>

<div class="flex flex-col">
	<div class="text-slate-600 text-sm">{label}</div>
	<div class="flex flex-row items-center">
		<div class="text-2xl {iconColor} mr-2"><i class={faIcon} /></div>
		<div class="text-3xl font-semibold">{count}</div>
	</div>
</div>
