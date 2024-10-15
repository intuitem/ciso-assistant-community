<script lang="ts">
	export let count: string = '0';
	export let label: string;
	// export let href: string | undefined = undefined;
	// export let help: string;
	export let icon: string;
	export let section: string;
	export let emphasis: boolean = false;
	let cEmphasis = '';
	if (emphasis) {
		cEmphasis = 'border border-y-0 border-r-0 border-l-2 border-l-violet-600';
	}
</script>

<div
	class="flex flex-col shadow-lg text-purple-800 p-2 h-28 bg-white hover:bg-violet-50 {cEmphasis}"
>
	<div class="text-xs">
		<span><i class={icon}></i></span>
		<span>{section}</span>
	</div>
	<div class="mt-auto">
		<div class="text-4xl font-bold text-left">{count}</div>
		<div class="text-sm">{label}</div>
	</div>
</div>

<style>
	@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

	.custom-font {
		font-family: 'Inter', sans-serif;
		font-optical-sizing: auto;
		font-style: normal;
	}
</style>
