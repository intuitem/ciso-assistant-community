import type { Meta, StoryObj } from '@storybook/svelte';

import RiskMatrix from './RiskMatrix.svelte';
import RiskScenarioItem from './RiskScenarioItem.svelte';

// More on how to set up stories at: https://storybook.js.org/docs/writing-stories
const meta = {
	title: 'Component/RiskMatrix',
	component: RiskMatrix,
	tags: ['autodocs']
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

const riskScenarios = [
	{
		id: '7059ef1b-7d4f-46bc-b735-ed41b531bb22',
		name: 'RS1',
		rid: 'R.1',
		strength_of_knowledge: {
			name: 'Low',
			description: 'The strength of the knowledge supporting the assessment is very high',
			symbol: '◇'
		}
	},
	{
		id: '7059ef1b-7d4f-46bc-b735-ed41b531bb22',
		name: 'RS1',
		rid: 'R.2',
		strength_of_knowledge: {
			name: 'Low',
			description: 'The strength of the knowledge supporting the assessment is very high',
			symbol: '⬙'
		}
	},
	{
		id: '7059ef1b-7d4f-46bc-b735-ed41b531bb22',
		name: 'RS1',
		rid: 'R.3',
		strength_of_knowledge: {
			name: 'Low',
			description: 'The strength of the knowledge supporting the assessment is very high',
			symbol: '◆'
		}
	},
	{
		id: '7059ef1b-7d4f-46bc-b735-ed41b531bb22',
		name: 'RS4',
		rid: 'R.1',
		strength_of_knowledge: {
			name: 'Low',
			description: 'The strength of the knowledge supporting the assessment is very high',
			symbol: '◆'
		}
	}
];

const sampleData = [
	[['R.1'], ['R.5'], ['R.8']],
	[['R.7'], [], ['R.9', 'R.6']],
	[['R.2'], ['R.3'], ['R.4']]
];

const sampleDataItems = [
	[[riskScenarios], [], []],
	[[], [], [riskScenarios, riskScenarios]],
	[[], [riskScenarios], []]
];

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {
	args: {
		riskMatrix: riskMatrix
	}
};

export const WithData: Story = {
	args: {
		riskMatrix: riskMatrix,
		data: sampleData
	}
};

export const WithRiskScenarioItemComponent: Story = {
	args: {
		riskMatrix: riskMatrix,
		data: sampleDataItems,
		dataItemComponent: RiskScenarioItem
	}
};
