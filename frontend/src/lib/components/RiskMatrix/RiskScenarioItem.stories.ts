import type { Meta, StoryObj } from '@storybook/svelte';

import RiskScenarioItem from './RiskScenarioItem.svelte';

// More on how to set up stories at: https://storybook.js.org/docs/writing-stories
const meta = {
	title: 'Component/RiskScenarioItem',
	component: RiskScenarioItem,
	tags: ['autodocs']
} satisfies Meta<RiskScenarioItem>;

export default meta;
type Story = StoryObj<typeof meta>;

const scenario = {
	id: '7059ef1b-7d4f-46bc-b735-ed41b531bb22',
	name: 'RS1',
	rid: 'R.1',
	strength_of_knowledge: {
		name: 'Very High',
		description: 'The strength of the knowledge supporting the assessment is very high',
		symbol: '●'
	}
};

export const Basic: Story = {
	args: {
		data: scenario
	}
};
