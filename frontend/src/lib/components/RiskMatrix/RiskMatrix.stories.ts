import type { Meta, StoryObj } from '@storybook/svelte';

import RiskMatrix from './RiskMatrix.svelte';

// More on how to set up stories at: https://storybook.js.org/docs/writing-stories
const meta = {
	title: 'Component/RiskMatrix',
	component: RiskMatrix
} satisfies Meta<RiskMatrix>;

const riskMatrix = {
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

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {
	render: () => ({
		Component: RiskMatrix,
		props: { riskMatrix: riskMatrix }
	})
};

export const WithData: Story = {
	render: () => ({
		Component: RiskMatrix,
		props: { riskMatrix: riskMatrix, data: sampleData }
	})
};
