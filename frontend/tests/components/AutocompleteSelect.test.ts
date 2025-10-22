/// <reference types="vitest" />
/// <reference types="@testing-library/jest-dom" />
import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/svelte';
import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
import { describe, test, expect } from 'vitest';

describe('AutocompleteSelect', () => {
    test('AutocompleteSelect is correctly rendered', () => {
        render(AutocompleteSelect, { props: { field: 'champstest', form: {} as any, onChange: () => null } });

        const selectOption = screen.getByTestId('form-input-champstest');
        expect(selectOption).toBeInTheDocument();
    });
});
