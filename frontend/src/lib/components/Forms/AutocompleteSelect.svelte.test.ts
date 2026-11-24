import { render, waitFor } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { get, type Writable } from 'svelte/store';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AutocompleteSelect from './AutocompleteSelect.svelte';

// svelte-multiselect reads prefers-reduced-motion at import; jsdom has no matchMedia.
vi.hoisted(() => {
	window.matchMedia ??= ((query: string) => ({
		matches: false,
		media: query,
		onchange: null,
		addEventListener: () => {},
		removeEventListener: () => {},
		addListener: () => {},
		removeListener: () => {},
		dispatchEvent: () => false
	})) as typeof window.matchMedia;
});

// The generated translations are tens of MB: loading them here for a few
// labels makes the coverage run exhaust the heap. Every message echoes its key.
vi.mock('#paraglide/messages.js', () => {
	const messages: object = new Proxy(
		{},
		{
			has: (_, key) => typeof key === 'string' && key !== 'then',
			get: (_, key) => {
				if (typeof key !== 'string' || key === 'then') return undefined;
				if (key === 'm') return messages;
				return (params?: Record<string, unknown>) =>
					params ? `${key} ${Object.values(params).join(' ')}` : key;
			}
		}
	);
	return messages;
});

const field = vi.hoisted(() => ({
	initial: undefined as unknown,
	value: undefined as unknown as Writable<unknown>
}));

vi.mock('sveltekit-superforms', async () => {
	const { writable } = await import('svelte/store');
	return {
		formFieldProxy: () => {
			field.value = writable(field.initial);
			return { value: field.value, errors: writable(undefined), constraints: writable({}) };
		}
	};
});

// formFieldProxy is mocked, so the form instance itself is never read.
const form = {} as ComponentProps<typeof AutocompleteSelect>['form'];

const ALICE = { id: 'a1', str: 'alice.active@example.com' };
// Deactivated: the actors endpoint only returns it with include_inactive=true.
const BOB = { id: 'b2', str: 'bob.departed@example.com' };

function stubActorsEndpoint(active = [ALICE]) {
	const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
		const url = new URL(String(input), 'http://localhost');
		const rows = url.searchParams.get('include_inactive') === 'true' ? [...active, BOB] : active;
		const ids = url.searchParams.get('id')?.split(',');
		const results = ids ? rows.filter((r) => ids.includes(r.id)) : rows;
		return {
			ok: true,
			json: async () => ({ count: results.length, next: null, previous: null, results })
		} as Response;
	});
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
}

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('AutocompleteSelect selected-value hydration', () => {
	it('keeps a current value the browsable list omits', async () => {
		const fetchMock = stubActorsEndpoint();
		field.initial = [ALICE.id, BOB.id];

		const { container } = render(AutocompleteSelect, {
			form,
			field: 'owner',
			multiple: true,
			optionsEndpoint: 'actors',
			optionsLabelField: 'str'
		});

		await waitFor(() => expect(container.textContent).toContain(BOB.str));
		expect(get(field.value)).toEqual([ALICE.id, BOB.id]);
		// Only the missing id is resolved, through the include_inactive switch.
		const hydration = fetchMock.mock.calls
			.map(([u]) => new URL(String(u), 'http://localhost'))
			.filter((u) => u.searchParams.has('id'));
		expect(hydration).toHaveLength(1);
		expect(hydration[0].searchParams.get('id')).toBe(BOB.id);
		expect(hydration[0].searchParams.get('include_inactive')).toBe('true');
	});

	it('names a deactivated owner and still counts an invisible one as hidden', async () => {
		stubActorsEndpoint();
		const invisible = 'c3';
		field.initial = [ALICE.id, BOB.id, invisible];

		const { container } = render(AutocompleteSelect, {
			props: {
				form,
				field: 'owner',
				multiple: true,
				optionsEndpoint: 'actors',
				optionsLabelField: 'str'
			},
			context: new Map([['formKeepsHiddenLinks', true]])
		});

		await waitFor(() => expect(container.textContent).toContain(BOB.str));
		const hidden = await waitFor(() => {
			const chip = container.querySelector('[data-testid="form-input-owner-hidden-links"]');
			expect(chip).not.toBeNull();
			return chip as Element;
		});
		expect(hidden.textContent).toContain('1');
		expect(get(field.value)).toEqual([ALICE.id, BOB.id, invisible]);
	});

	it('clears the missing-options flag once the only value is resolved', async () => {
		stubActorsEndpoint([]);
		field.initial = [BOB.id];
		const updateMissingConstraint = vi.fn();

		const { container } = render(AutocompleteSelect, {
			props: {
				form,
				field: 'owner',
				multiple: true,
				mandatory: true,
				optionsEndpoint: 'actors',
				optionsLabelField: 'str'
			},
			context: new Map([['updateMissingConstraint', updateMissingConstraint]])
		});

		await waitFor(() => expect(container.textContent).toContain(BOB.str));
		expect(updateMissingConstraint.mock.calls).toEqual([
			['owner', true],
			['owner', false]
		]);
	});

	it('does not resolve by id when every value is already listed', async () => {
		const fetchMock = stubActorsEndpoint();
		field.initial = [ALICE.id];

		const { container } = render(AutocompleteSelect, {
			form,
			field: 'owner',
			multiple: true,
			optionsEndpoint: 'actors',
			optionsLabelField: 'str'
		});

		await waitFor(() => expect(container.textContent).toContain(ALICE.str));
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});

	it('does not resolve by id for fields whose value is not an id', async () => {
		const fetchMock = stubActorsEndpoint();
		field.initial = 'urn:missing';

		render(AutocompleteSelect, {
			form,
			field: 'framework',
			optionsEndpoint: 'actors',
			optionsLabelField: 'str',
			optionsValueField: 'urn'
		});

		await waitFor(() => expect(fetchMock).toHaveBeenCalled());
		await new Promise((r) => setTimeout(r, 50));
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});
});
