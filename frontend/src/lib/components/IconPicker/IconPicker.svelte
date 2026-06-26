<script lang="ts">
	let { value = $bindable(''), showInput = true }: { value: string; showInput?: boolean } =
		$props();
	let open = $state(false);

	const ICONS = [
		'fa-star',
		'fa-bolt',
		'fa-rocket',
		'fa-wand-magic-sparkles',
		'fa-flag',
		'fa-bell',
		'fa-clipboard-check',
		'fa-clipboard-list',
		'fa-list-check',
		'fa-file',
		'fa-file-lines',
		'fa-file-shield',
		'fa-book',
		'fa-folder',
		'fa-certificate',
		'fa-scale-balanced',
		'fa-shield-halved',
		'fa-lock',
		'fa-key',
		'fa-fingerprint',
		'fa-user-shield',
		'fa-triangle-exclamation',
		'fa-bug',
		'fa-fire-extinguisher',
		'fa-circle-info',
		'fa-circle-question',
		'fa-gauge',
		'fa-chart-line',
		'fa-chart-pie',
		'fa-diagram-project',
		'fa-sitemap',
		'fa-gem',
		'fa-building',
		'fa-handshake',
		'fa-users',
		'fa-user',
		'fa-gear',
		'fa-sliders',
		'fa-magnifying-glass',
		'fa-calendar',
		'fa-clock',
		'fa-envelope',
		'fa-globe',
		'fa-link',
		'fa-cloud',
		'fa-server',
		'fa-database',
		'fa-eye'
	];

	function pick(icon: string) {
		value = icon;
		open = false;
	}
</script>

<div class="relative inline-block">
	<div class="flex items-center gap-1">
		<button
			type="button"
			onclick={() => (open = !open)}
			aria-label="Pick icon"
			class="flex h-8 w-8 items-center justify-center rounded-md border border-surface-200-800 text-violet-500 hover:bg-surface-100-900 cursor-pointer"
		>
			<i class="fa-solid {value || 'fa-star'}"></i>
		</button>
		{#if showInput}
			<input bind:value placeholder="fa-bolt" class="input rounded-md text-sm w-24" />
		{/if}
	</div>
	{#if open}
		<button
			type="button"
			class="fixed inset-0 z-40 cursor-default"
			onclick={() => (open = false)}
			aria-label="Close icon picker"
			tabindex="-1"
		></button>
		<div
			class="absolute left-0 z-50 mt-1 grid w-64 grid-cols-8 gap-1 rounded-lg border border-surface-200-800 bg-surface-50-950 p-2 shadow-xl"
		>
			{#each ICONS as icon}
				<button
					type="button"
					onclick={() => pick(icon)}
					title={icon}
					aria-label={icon}
					class="flex h-7 w-7 items-center justify-center rounded hover:bg-surface-100-900 {value ===
					icon
						? 'bg-violet-500/15 text-violet-600'
						: 'text-surface-600-400'}"
				>
					<i class="fa-solid {icon}"></i>
				</button>
			{/each}
		</div>
	{/if}
</div>
