<script lang="ts">
	import { page } from '$app/stores';
	import { localItems } from '$lib/utils/locales';
	import { breadcrumbObject, pageTitle } from '$lib/utils/stores';
	import { listViewFields } from '$lib/utils/table';
	import * as m from '$paraglide/messages';
	import { languageTag } from '$paraglide/runtime';

	let crumbs: Array<{ label: string; href: string; icon?: string }> = [];

	function capitalizeSecondWord(sentence: string) {
		var words = sentence.split(' ');

		if (words.length >= 2) {
			words[1] = words[1].charAt(0).toUpperCase() + words[1].substring(1);
			return words.join('');
		} else {
			return sentence;
		}
	}

	$: {
		// Remove zero-length tokens.
		const tokens = $page.url.pathname.split('/').filter((t) => t !== '');
		let title = '';

		// Create { label, href } pairs for each token.
		let tokenPath = '';
		crumbs = tokens.map((t) => {
			tokenPath += '/' + t;
			if (t === $breadcrumbObject.id) {
				if ($breadcrumbObject.name) {
					t = $breadcrumbObject.name;
				} else if ($breadcrumbObject.first_name && $breadcrumbObject.last_name) {
					t = `${$breadcrumbObject.first_name} ${$breadcrumbObject.last_name}`;
				} else {
					t = $breadcrumbObject.email;
				}
			} else if (t === 'folders') {
				t = 'domains';
			} else {
				t = t.replace(/-/g, ' ');
				t = capitalizeSecondWord(t);
			}
			return {
				label: $page.data.label || t,
				href:
					Object.keys(listViewFields).includes(tokens[0]) &&
					!listViewFields[tokens[0]].breadcrumb_link_disabled
						? tokenPath
						: null
			};
		});

		crumbs.unshift({ label: m.home(), href: '/', icon: 'fa-regular fa-compass' });
		if (crumbs[crumbs.length - 1].label != 'edit') pageTitle.set(crumbs[crumbs.length - 1].label);
		else pageTitle.set(m.edit() + ' ' + crumbs[crumbs.length - 2].label);
	}
</script>

<ol class="breadcrumb-nonresponsive">
	{#each crumbs as c, i}
		{#if i == crumbs.length - 1}
			<span class="text-sm text-gray-500 font-semibold antialiased" data-testid="crumb-item">
				{#if c.icon}
					<i class={c.icon} />
				{/if}
				{#if localItems()[c.label]}
					{localItems()[c.label]}
				{:else}
					{c.label}
				{/if}
			</span>
		{:else}
			<li class="crumb">
				{#if c.href}
					<a
						class="unstyled text-sm hover:text-primary-500 font-semibold antialiased whitespace-nowrap"
						data-testid="crumb-item"
						href={c.href}
					>
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{#if localItems()[c.label]}
							{localItems()[c.label]}
						{:else}
							{c.label}
						{/if}
					</a>
				{:else}
					<span class="text-sm text-gray-500 font-semibold antialiased" data-testid="crumb-item">
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{#if localItems()[c.label]}
							{localItems()[c.label]}
						{:else}
							{c.label}
						{/if}
					</span>
				{/if}
			</li>
			<li class="crumb-separator" aria-hidden>&rsaquo;</li>
		{/if}
	{/each}
</ol>
