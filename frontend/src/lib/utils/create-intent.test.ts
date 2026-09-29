import { beforeEach, describe, expect, it, vi } from 'vitest';

import { page } from '$app/state';
import { CREATE_INTENT_PARAM, consumeCreateIntent, createIntentHref } from './create-intent';

const ROOT = '00000000-0000-0000-0000-000000000000';

function at(url: string) {
	// SvelteKit narrows `pathname` to its known routes; a test URL is a plain one.
	page.url = new URL(url, 'http://localhost') as typeof page.url;
}

beforeEach(() => {
	page.data = {
		user: { root_folder_id: ROOT, domain_permissions: { [ROOT]: ['add_asset'] } }
	};
});

describe('consumeCreateIntent', () => {
	const intent = (open: () => void) => ({ urlModel: 'assets', modelName: 'asset', open });

	it('opens the form when the intent names this page', () => {
		at(createIntentHref('/assets'));
		const open = vi.fn();
		consumeCreateIntent(intent(open));
		expect(open).toHaveBeenCalledOnce();
	});

	it('does nothing without an intent in the URL', () => {
		at('/assets');
		const open = vi.fn();
		consumeCreateIntent(intent(open));
		expect(open).not.toHaveBeenCalled();
	});

	/**
	 * The outgoing page sees the incoming URL before it is torn down. Without the pathname
	 * guard, navigating /assets -> /ebios-rm opened the asset form on top of the EBIOS one.
	 */
	it('ignores an intent addressed to a different page', () => {
		at(createIntentHref('/ebios-rm'));
		const open = vi.fn();
		consumeCreateIntent(intent(open));
		expect(open).not.toHaveBeenCalled();
	});

	it('refuses a model that is never created from its list page', () => {
		at(createIntentHref('/frameworks'));
		const open = vi.fn();
		consumeCreateIntent({ urlModel: 'frameworks', modelName: 'framework', open });
		expect(open).not.toHaveBeenCalled();
	});

	it('refuses a hand-typed intent the user lacks permission for', () => {
		at(createIntentHref('/threats'));
		const open = vi.fn();
		consumeCreateIntent({ urlModel: 'threats', modelName: 'threat', open });
		expect(open).not.toHaveBeenCalled();
	});

	it('strips the parameter from the address bar', () => {
		at(createIntentHref('/assets'));
		consumeCreateIntent(intent(vi.fn()));
		expect(new URL(window.location.href).searchParams.has(CREATE_INTENT_PARAM)).toBe(false);
		expect(new URL(window.location.href).pathname).toBe('/assets');
	});
});
