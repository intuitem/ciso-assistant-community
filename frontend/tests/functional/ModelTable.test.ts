import { render, screen } from '@testing-library/svelte';
import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';

const source = {
	head: { id: 'ID', name: 'Name', tags: 'Tags' },
	body: [
		{ id: '1', name: 'Jean', tags: ['a', 'b'], meta: { id: '1' } },
		{ id: '2', name: 'Patoche', tags: ['c'], meta: { id: '2' } }
	],
	meta: { count: 2 }
};

describe('ModelTable', () => {
	it('renders headers and rows', async () => {
		render(ModelTable, { props: { source, URLModel: 'test-model', displayActions: false } });

		expect(screen.getByText('ID')).toBeTruthy();
		expect(screen.getByText('Name')).toBeTruthy();

		expect(screen.getByText('Jean')).toBeTruthy();
		expect(screen.getByText('Patoche')).toBeTruthy();
	});

	it('renders actions column when displayActions=true', async () => {
		render(ModelTable, { props: { source, URLModel: 'test-model', displayActions: true } });

		const actionHeader = document.querySelector('th.text-end');
		expect(actionHeader).toBeTruthy();
	});
});
