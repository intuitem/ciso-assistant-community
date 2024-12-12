<script lang="ts">
	import { breadcrumbs } from '$lib/utils/breadcrumbs';
	import { safeTranslate } from '$lib/utils/i18n';
</script>

<ol class="breadcrumb-nonresponsive">
	{#each $breadcrumbs as c, i}
		{#if i == $breadcrumbs.length - 1}
			<span class="text-sm text-gray-500 font-semibold antialiased" data-testid="crumb-item">
				{#if c.icon}
					<i class={c.icon} />
				{/if}
				{safeTranslate(c.label)}
			</span>
		{:else}
			<li class="crumb">
				{#if c.href}
					<a
						class="unstyled text-sm hover:text-primary-500 font-semibold antialiased whitespace-nowrap"
						data-testid="crumb-item"
						href={c.href}
						on:click={() => breadcrumbs.slice(i)}
					>
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{safeTranslate(c.label)}
					</a>
				{:else}
					<span class="text-sm text-gray-500 font-semibold antialiased" data-testid="crumb-item">
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{safeTranslate(c.label)}
					</span>
				{/if}
			</li>
			<li class="crumb-separator" aria-hidden>&rsaquo;</li>
		{/if}
	{/each}
</ol>
