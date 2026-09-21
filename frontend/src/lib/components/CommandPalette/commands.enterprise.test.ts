import { describe, expect, it, vi } from 'vitest';

import type { User } from '$lib/utils/types';

// The Enterprise overlay REPLACES `SideBar/navData.ts` wholesale (see
// `enterprise/frontend/Makefile` `pre-build`), and its copy lists pages the community sidebar
// does not — `/service-accounts` among them, which `EXTRA_DESTINATIONS` also carries. Two
// navigation commands with the same href collide on the palette's keyed `{#each}` and Svelte
// throws `each_key_duplicate`, so the palette renders nothing at all in Enterprise while
// community is fine. This file pins the Enterprise-shaped sidebar.
vi.mock('../SideBar/navData', () => ({
	navData: {
		items: [
			{
				name: 'organisation',
				items: [
					{ name: 'folders', fa_icon: 'fa-solid fa-sitemap', href: '/folders' },
					// Enterprise-only entry, overlapping an EXTRA_DESTINATIONS href.
					{
						name: 'serviceAccounts',
						fa_icon: 'fa-solid fa-robot',
						href: '/service-accounts',
						adminOnly: true
					}
				]
			}
		]
	}
}));

// `vi.mock` is hoisted above this, so `commands` sees the Enterprise sidebar.
import { buildNavigationCommands } from './commands';

const ROOT = '00000000-0000-0000-0000-000000000000';

const admin = {
	root_folder_id: ROOT,
	is_admin: true,
	roles: ['BI-RL-GLA'],
	domain_permissions: { [ROOT]: ['view_folder', 'view_serviceaccount'] }
} as unknown as User;

const allFlags = new Proxy({}, { get: () => true }) as Record<string, boolean>;

describe('buildNavigationCommands with the Enterprise sidebar', () => {
	it('offers each destination exactly once', () => {
		const hrefs = buildNavigationCommands(admin, allFlags).map((command) => command.href);
		expect(hrefs).toContain('/service-accounts');
		expect(new Set(hrefs).size).toBe(hrefs.length);
	});

	// The sidebar entry is the one kept, so it is the edition's own rules that apply.
	it('still hides the admin-only sidebar entry from a non-admin', () => {
		const nonAdmin = { ...admin, is_admin: false } as unknown as User;
		const hrefs = buildNavigationCommands(nonAdmin, allFlags).map((command) => command.href);
		expect(hrefs).not.toContain('/service-accounts');
	});
});
