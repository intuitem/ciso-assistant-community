import { render } from '@testing-library/svelte';
import { within } from '@testing-library/dom';
import { describe, it, expect } from 'vitest';
import { computePosition, autoUpdate, offset, shift, flip, arrow } from '@floating-ui/dom';
import { storePopup } from '@skeletonlabs/skeleton';
storePopup.set({ computePosition, autoUpdate, offset, shift, flip, arrow });

import Matrix from './RiskMatrix.svelte';
import type { RiskMatrix } from '$lib/utils/types';

const riskMatrix: RiskMatrix = {
	locale: 'en',
	name: 'FAIR risk matrix',
	description: 'Balanced 3x3 risk matrix inspired from FAIR',
	format_version: '1.0',
	json_definition: JSON.stringify({
		name: 'balanced',
		description: 'inspired from FAIR',
		probability: [
			{ abbreviation: 'L', name: 'Low', description: 'Unfrequent event' },
			{ abbreviation: 'M', name: 'Medium', description: 'Occasional event' },
			{ abbreviation: 'H', name: 'High', description: 'Frequent event' }
		],
		impact: [
			{ abbreviation: 'L', name: 'Low', description: 'Low impact' },
			{ abbreviation: 'M', name: 'Medium', description: 'Medium impact' },
			{ abbreviation: 'H', name: 'High', description: 'High impact' }
		],
		risk: [
			{ abbreviation: 'L', name: 'Low', description: 'acceptable risk', hexcolor: '#00FF00' },
			{
				abbreviation: 'M',
				name: 'Medium',
				description: 'risk requiring mitigation within 2 years',
				hexcolor: '#FFFF00'
			},
			{ abbreviation: 'H', name: 'High', description: 'unacceptable risk', hexcolor: '#FF0000' }
		],
		grid: [
			[0, 0, 1],
			[0, 1, 1],
			[1, 1, 2]
		]
	})
};

const sampleData = [
	[['R.1'], ['R.5'], ['R.8']],
	[['R.7'], [], ['R.9', 'R.6']],
	[['R.2'], ['R.3'], ['R.4']]
];

describe('RiskMatrix.svelte', () => {
	it('Renders with minimal props', async () => {
		const { getByTestId } = render(Matrix, {
			props: {
				riskMatrix: riskMatrix
			}
		});
		const element: HTMLElement = getByTestId('risk-matrix');
		expect(element).toBeTruthy();
		expect(element.tagName).eq('DIV');
		const cells = within(element).getAllByTestId('cell');
		expect(cells.length).eq(9);
	});
	it('Renders with empty data', async () => {
		const { getByTestId } = render(Matrix, {
			props: {
				riskMatrix: riskMatrix,
				data: []
			}
		});
		const element: HTMLElement = getByTestId('risk-matrix');
		expect(element).toBeTruthy();
		expect(element.tagName).eq('DIV');
		const cells = within(element).getAllByTestId('cell');
		expect(cells.length).eq(9);
	});
	it('Renders with sample data', async () => {
		const { getByTestId } = render(Matrix, {
			props: {
				riskMatrix: riskMatrix,
				data: sampleData
			}
		});
		const element: HTMLElement = getByTestId('risk-matrix');
		expect(element).toBeTruthy();
		expect(element.tagName).eq('DIV');
		const cells = within(element).getAllByTestId('cell');
		expect(cells.length).eq(9);
	});
	it('Renders probability names and descriptions in the right order', async () => {
		const { getByTestId } = render(Matrix, {
			props: {
				riskMatrix: riskMatrix,
				data: sampleData
			}
		});
		const element: HTMLElement = getByTestId('risk-matrix');
		const cells: HTMLElement[] = within(element).getAllByTestId('probability-row-header');
		expect(cells.length).eq(3);
		// NOTE: High to low because we iterate from top to bottom on display
		const expectedNames = ['High', 'Medium', 'Low'];
		const expectedDescriptions = ['Frequent event', 'Occasional event', 'Unfrequent event'];
		for (let i = 0; i < expectedNames.length; i++) {
			const name = within(cells[i]).getByTestId('probability-name');
			const description = within(cells[i]).getByTestId('probability-description');
			expect(name.textContent).eq(expectedNames[i]);
			expect(description.textContent).eq(expectedDescriptions[i]);
		}
	});
	it('Renders impact names and descriptions in the right order', async () => {
		const { getByTestId } = render(Matrix, {
			props: {
				riskMatrix: riskMatrix,
				data: sampleData
			}
		});
		const element: HTMLElement = getByTestId('risk-matrix');
		const cells: HTMLElement[] = within(element).getAllByTestId('impact-col-header');
		const expectedNames = ['Low', 'Medium', 'High'];
		const expectedDescriptions = ['Low impact', 'Medium impact', 'High impact'];
		for (let i = 0; i < expectedNames.length; i++) {
			const name = within(cells[i]).getByTestId('impact-name');
			const description = within(cells[i]).getByTestId('impact-description');
			expect(name.textContent).eq(expectedNames[i]);
			expect(description.textContent).eq(expectedDescriptions[i]);
		}
	});
});

describe('Data Rendering', () => {
	it('Renders data elements in the right cells', async () => {
		const { getByTestId } = render(Matrix, {
			props: {
				riskMatrix: riskMatrix,
				data: sampleData
			}
		});
		const element: HTMLElement = getByTestId('risk-matrix');
		const cells: HTMLElement[] = within(element).getAllByTestId('cell');

		const expectedTexts = [
			['R.2', 'R.3', 'R.4'],
			['R.7', '', 'R.9,R.6'],
			['R.1', 'R.5', 'R.8']
		];

		let cellIndex = 0;
		for (let i = 0; i < expectedTexts.length; i++) {
			for (let j = 0; j < expectedTexts[i].length; j++) {
				expect(cells[cellIndex++].textContent).eq(expectedTexts[i][j]);
			}
		}
	});
});
