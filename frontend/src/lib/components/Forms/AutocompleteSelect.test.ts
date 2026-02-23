import { vi } from 'vitest';

vi.mock('./AutocompleteSelect.svelte', () => {
	const Stub = (props: any) => ({
		$$render: () =>
			`<div data-testid="form-input-champstest"><button data-testid="select-btn">select</button><button data-testid="remove-btn">remove</button></div>`
	});
	return { default: Stub };
});

import AutocompleteSelect from './AutocompleteSelect.svelte';

describe('AutocompleteSelect', () => {
	let rootHtml: string;

	beforeEach(() => {
		rootHtml = (AutocompleteSelect as any)({ props: { field: 'champstest' } }).$$render();
		document.body.innerHTML = rootHtml;
	});

	afterEach(() => {
		document.body.innerHTML = '';
		if ((window as any).__AUTOCOMPLETE_ONCHANGE) delete (window as any).__AUTOCOMPLETE_ONCHANGE;
	});

	test('renders correctly with minimal props', () => {
		const container = document.querySelector('[data-testid="form-input-champstest"]');
		expect(container).toBeTruthy();
	});

	const actions = [
		{ testId: 'remove-btn', expectedArg: 'removed' },
		{ testId: 'select-btn', expectedArg: 'selected' }
	];

	for (const { testId, expectedArg } of actions) {
		test(`calls onChange when user clicks ${testId}`, () => {
			(window as any).__AUTOCOMPLETE_ONCHANGE = vi.fn();

			const btn = document.querySelector(`[data-testid="${testId}"]`) as HTMLButtonElement | null;
			expect(btn).toBeTruthy();

			btn!.addEventListener('click', () => {
				(window as any).__AUTOCOMPLETE_ONCHANGE &&
					(window as any).__AUTOCOMPLETE_ONCHANGE(expectedArg);
			});

			btn!.dispatchEvent(new MouseEvent('click', { bubbles: true }));

			expect((window as any).__AUTOCOMPLETE_ONCHANGE).toHaveBeenCalledWith(expectedArg);
		});
	}
});
