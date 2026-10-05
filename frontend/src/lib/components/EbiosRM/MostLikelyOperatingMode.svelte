<script lang="ts">
	import { m } from '$paraglide/messages';
	import { isDark } from '$lib/utils/helpers';

	interface Props {
		operatingMode: {
			id: string;
			str: string;
			likelihood: { name?: string; hexcolor?: string };
			critical_steps: { id: string; name: string }[];
		} | null;
		linked?: boolean;
	}

	let { operatingMode, linked = true }: Props = $props();
</script>

{#if operatingMode}
	<div
		class="rounded-md border border-primary-200-800 bg-primary-50 dark:bg-primary-950/40 px-3 py-2 text-sm space-y-1"
		data-testid="most-likely-operating-mode"
	>
		<p class="flex flex-wrap items-center gap-2">
			<i class="fa-solid fa-crosshairs text-primary-600-400"></i>
			<span class="font-semibold text-surface-700-300">{m.mostLikelyOperatingMode()}</span>
			{#if linked}
				<a href="/operating-modes/{operatingMode.id}" class="anchor">{operatingMode.str}</a>
			{:else}
				<span>{operatingMode.str}</span>
			{/if}
			{#if operatingMode.likelihood?.name}
				<span
					class="badge text-xs {operatingMode.likelihood.hexcolor &&
					!isDark(operatingMode.likelihood.hexcolor)
						? 'text-surface-950'
						: ''}"
					style={operatingMode.likelihood.hexcolor
						? `background-color: ${operatingMode.likelihood.hexcolor}`
						: ''}>{operatingMode.likelihood.name}</span
				>
			{/if}
		</p>
		{#if operatingMode.critical_steps.length}
			<p class="flex flex-wrap items-center gap-1 text-xs text-surface-600-400">
				<span class="font-semibold">{m.criticalPath()}</span>
				{#each operatingMode.critical_steps as step, index}
					{#if index > 0}<i class="fa-solid fa-arrow-right text-[9px] text-error-500"></i>{/if}
					<span class="text-error-700-300">{step.name}</span>
				{/each}
			</p>
		{/if}
	</div>
{/if}
