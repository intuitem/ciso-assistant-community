/// <reference types="vitest" />
/// <reference types="@testing-library/jest-dom" />
import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/svelte';
import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
import { describe, test, expect } from 'vitest';

describe('ModelTable', () => {
	const source = {
		head: { id: 'ID', name: 'Name', tags: 'Tags' },
		body: [
			{ id: '1', name: 'Jean', tags: ['a', 'b'], meta: { id: '1' } },
			{ id: '2', name: 'Patoche', tags: ['c'], meta: { id: '2' } }
		],
		meta: { count: 2 }
	};
	test('renders headers and rows', async () => {
		render(ModelTable, { props: { source, URLModel: 'test-model' as any, displayActions: false } });

		expect(screen.getByText('ID')).toBeInTheDocument();
		expect(screen.getByText('Name')).toBeInTheDocument();

		expect(screen.getByText('Jean')).toBeInTheDocument();
		expect(screen.getByText('Patoche')).toBeTruthy();
	});

	test('renders actions column when displayActions=true', () => {
		render(ModelTable, { props: { source, URLModel: 'test-model' as any, displayActions: true } });

		expect(screen.getByRole('columnheader', { name: /actions/i })).toBeInTheDocument();
	});
});
