<script lang="ts">
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';

	const tabs = [
		{ href: '/connected-apps', label: m.connections, testid: 'connections-tab' },
		{ href: '/connection-profiles', label: m.connectionProfiles, testid: 'profiles-tab' }
	];
</script>

<nav class="flex gap-1 border-b border-surface-200-800 mb-4">
	{#each tabs as tab}
		{@const active = page.url.pathname.startsWith(tab.href)}
		<a
			href={tab.href}
			data-testid={tab.testid}
			aria-current={active ? 'page' : undefined}
			class="px-4 py-2 -mb-px border-b-2 text-sm font-medium {active
				? 'border-primary-500 text-primary-600'
				: 'border-transparent text-surface-600-400 hover:text-primary-500'}">{tab.label()}</a
		>
	{/each}
</nav>
