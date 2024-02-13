<script lang="ts">
	import { page } from '$app/stores';
	import { breadcrumbObject, pageTitle } from '$lib/utils/stores';
	import { listViewFields } from '$lib/utils/table';
	import * as m from '$paraglide/messages';

	const breadcrumbsItems: any = {
		edit: m.edit(),
		analytics: m.analytics(),
		calendar: m.calendar(),
		threats: m.threats(),
		securityFunctions: m.securityFunctions(),
		securityMeasures: m.securityMeasures(),
		assets: m.assets(),
		policies: m.policies(),
		riskMatrices: m.riskMatrices(),
		riskAssessments: m.riskAssessments(),
		riskScenarios: m.riskScenarios(),
		riskAcceptances: m.riskAcceptances(),
		complianceAssessments: m.complianceAssessments(),
		evidences: m.evidences(),
		frameworks: m.frameworks(),
		domains: m.domains(),
		projects: m.projects(),
		users: m.users(),
		userGroups: m.userGroups(),
		roleAssignments: m.roleAssignments(),
		xRays: m.xRays(),
		scoringAssistant: m.scoringAssistant(),
		libraries: m.libraries(),
		backupRestore: m.backupRestore()
	}

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
			t = t.replace(/-/g, ' ');
			t = capitalizeSecondWord(t);
			return {
				label: $page.data.label || t,
				href: Object.keys(listViewFields).includes(tokens[0]) ? tokenPath : null
			};
		});

		crumbs.unshift({ label: m.home(), href: '/', icon: 'fa-regular fa-compass' });
		if (crumbs[crumbs.length - 1].label != 'edit') pageTitle.set(crumbs[crumbs.length - 1].label);
		else pageTitle.set(m.edit()+ ' ' + crumbs[crumbs.length - 2].label);
	}
</script>

<ol class="breadcrumb-nonresponsive">
	{#each crumbs as c, i}
		{#if i == crumbs.length - 1}
			<span class="text-sm text-gray-500 font-semibold antialiased">
				{#if c.icon}
					<i class={c.icon} />
				{/if}
				{#if breadcrumbsItems[c.label]}
					{breadcrumbsItems[c.label]}
				{:else}
					{c.label}
				{/if}
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
						{#if breadcrumbsItems[c.label]}
							{breadcrumbsItems[c.label]}
						{:else}
							{c.label}
						{/if}
					</a>
				{:else}
					<span class="text-sm text-gray-500 font-semibold antialiased">
						{#if c.icon}
							<i class={c.icon} />
						{/if}
						{#if breadcrumbsItems[c.label]}
							{breadcrumbsItems[c.label]}
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
