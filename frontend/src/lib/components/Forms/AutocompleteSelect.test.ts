import AutocompleteSelect from './AutocompleteSelect.svelte';
import { flushSync, mount, type ComponentProps } from 'svelte';
import { render, screen } from '@testing-library/svelte';
import { vi } from 'vitest';

vi.mock('svelte', () => {
    const originalModule = vi.importActual('svelte');
    return {
        ...originalModule,
        onMount: vi.fn(),
        mount: vi.fn(),
        flushSync: vi.fn(),
        tick: vi.fn(),
    };
});


describe('AutocompleteSelect', () => {
    test('renders correctly with minimal props', () => {
        render(AutocompleteSelect, { props: { field: 'champstest', form: {} as any, onChange: () => null } });

        const select = screen.getByTestId('form-input-champstest');
        expect(select).toBeInTheDocument();
    });
});
