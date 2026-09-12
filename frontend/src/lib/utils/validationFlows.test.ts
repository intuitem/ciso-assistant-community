import { describe, expect, it } from 'vitest';

import { validationFlowLinkedObjects } from './validationFlows';

describe('validationFlowLinkedObjects', () => {
	it('keeps a staged risk approval out of the generic linked-object list', () => {
		const flow = {
			risk_scenario: { id: 'risk-1', ref_id: 'RISK-001', name: 'Service outage' },
			risk_approval_stage: 'assessment'
		};

		expect(validationFlowLinkedObjects(flow)).toEqual([]);
	});

	it('renders a legacy risk link when no approval stage is set', () => {
		const riskScenario = { id: 'risk-1', ref_id: 'RISK-001', name: 'Service outage' };
		const flow = { risk_scenario: riskScenario, risk_approval_stage: '' };

		expect(validationFlowLinkedObjects(flow)).toEqual([
			{
				key: 'risk_scenarios',
				item: riskScenario,
				href: '/risk-scenarios/risk-1'
			}
		]);
	});
});
