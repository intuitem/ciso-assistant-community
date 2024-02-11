<script lang="ts">
	import { page } from '$app/stores';
	import { breadcrumbObject, pageTitle } from '$lib/utils/stores';
	import { listViewFields } from '$lib/utils/table';

	let crumbs: Array<{ label: string; href: string; icon?: string }> = [];

	$: {
		// Remove zero-length tokens.
		const tokens = $page.url.pathname.split('/').filter((t) => t !== '');

		// Create { label, href } pairs for each token.
		let tokenPath = '';
		crumbs = tokens.map((t) => {
			tokenPath += '/' + t;
			if (t === $breadcrumbObject.id) {
				if ($breadcrumbObject.name) t = $breadcrumbObject.name;
				else t = $breadcrumbObject.email;
			} else if (t === 'folders') {
				t = 'domains';
			}
			t = t.charAt(0).toUpperCase() + t.slice(1);
			t = t.replace(/-/g, ' ');
			return {
				label: $page.data.label || t,
				href: Object.keys(listViewFields).includes(tokens[0]) ? tokenPath : null
			};
		});

		crumbs.unshift({ label: 'Home', href: '/', icon: 'fa-regular fa-compass' });
		if (crumbs[crumbs.length - 1].label != 'Edit') pageTitle.set(crumbs[crumbs.length - 1].label);
		else pageTitle.set('Edit ' + crumbs[crumbs.length - 2].label);
	}
</script>

<ol class="breadcrumb-nonresponsive">
	{#each crumbs as c, i}
		{#if i == crumbs.length - 1}
			<span class="text-sm text-gray-500 font-semibold antialiased">
				{#if c.icon}
					<i class={c.icon} />
				{/if}
				{c.label}
			</span>
		{:else}
			<li class="crumb">
				{#if c.href}
					<a
						class="unstyled text-sm hover:text-primary-500 font-semibold antialiased whitespace-nowrap"
						href={c.href}
					>
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{c.label}
					</a>
				{:else}
					<span class="text-sm text-gray-500 font-semibold antialiased">
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{c.label}
					</span>
				{/if}
			</li>
			<li class="crumb-separator" aria-hidden>&rsaquo;</li>
		{/if}
	{/each}
</ol>
