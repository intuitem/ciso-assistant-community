export const forms = {
	threat_agent: [
		{
			id: 'skill_level',
			text: 'skillLevelText',
			choices: [
				'NA',
				'skillLevelChoice1',
				null,
				'skillLevelChoice2',
				null,
				'skillLevelChoice3',
				'skillLevelChoice4',
				null,
				null,
				'skillLevelChoice5'
			]
		},
		{
			id: 'motive',
			text: 'motiveText',
			choices: [
				'NA',
				'motiveChoice1',
				null,
				null,
				'motiveChoice2',
				null,
				null,
				null,
				null,
				'motiveChoice3'
			]
		},
		{
			id: 'opportunity',
			text: 'opportunityText',
			choices: [
				'opportunityChoice1',
				null,
				null,
				null,
				'opportunityChoice2',
				null,
				null,
				'opportunityChoice3',
				null,
				'opportunityChoice4'
			]
		},
		{
			id: 'size',
			text: 'sizeText',
			choices: [
				'NA',
				null,
				'sizeChoice1',
				null,
				'sizeChoice2',
				'sizeChoice3',
				'sizeChoice4',
				null,
				null,
				'sizeChoice5'
			]
		}
	],
	vulnerability: [
		{
			id: 'ease_of_discovery',
			text: 'easeOfDiscoveryText',
			choices: [
				'NA',
				'easeOfDiscoveryChoice1',
				null,
				'easeOfDiscoveryChoice2',
				null,
				null,
				null,
				'easeOfDiscoveryChoice3',
				null,
				'easeOfDiscoveryChoice4'
			]
		},
		{
			id: 'ease_of_exploit',
			text: 'easeOfExploitText',
			choices: [
				'NA',
				'easeOfExploitChoice1',
				null,
				'easeOfExploitChoice2',
				null,
				'easeOfExploitChoice3',
				null,
				null,
				null,
				'easeOfExploitChoice4'
			]
		},
		{
			id: 'awareness',
			text: 'awarenessText',
			choices: [
				'NA',
				'awarenessChoice1',
				null,
				null,
				'awarenessChoice2',
				null,
				'awarenessChoice3',
				null,
				null,
				'awarenessChoice4'
			]
		},
		{
			id: 'intrusion_detection',
			text: 'intrusionDetectionText',
			choices: [
				'NA',
				'intrusionDetectionChoice1',
				null,
				'intrusionDetectionChoice2',
				null,
				null,
				null,
				null,
				'intrusionDetectionChoice3',
				'intrusionDetectionChoice4'
			]
		}
	],
	business_impact: [
		{
			id: 'financial_damage',
			text: 'financialDamageText',
			choices: [
				'NA',
				'financialDamageChoice1',
				null,
				'financialDamageChoice2',
				null,
				null,
				null,
				'financialDamageChoice3',
				null,
				'financialDamageChoice4'
			]
		},
		{
			id: 'reputation_damage',
			text: 'reputationDamageText',
			choices: [
				'NA',
				'reputationDamageChoice1',
				null,
				null,
				'reputationDamageChoice2',
				'reputationDamageChoice3',
				null,
				null,
				null,
				'reputationDamageChoice4'
			]
		},
		{
			id: 'non_compliance',
			text: 'nonComplianceText',
			choices: [
				'NA',
				null,
				'nonComplianceChoice1',
				null,
				null,
				'nonComplianceChoice2',
				null,
				'nonComplianceChoice3',
				null,
				'nonComplianceChoice4'
			]
		},
		{
			id: 'privacy_violation',
			text: 'privacyViolationText',
			choices: [
				'NA',
				null,
				null,
				'privacyViolationChoice1',
				null,
				'privacyViolationChoice2',
				null,
				'privacyViolationChoice3',
				null,
				'privacyViolationChoice4'
			]
		}
	],
	technical_impact: [
		{
			id: 'loss_of_confidentiality',
			text: 'lossOfConfidentialityText',
			choices: [
				'NA',
				null,
				'lossOfConfidentialityChoice1',
				null,
				null,
				null,
				'lossOfConfidentialityChoice2',
				'lossOfConfidentialityChoice3',
				null,
				'lossOfConfidentialityChoice4'
			]
		},
		{
			id: 'loss_of_integrity',
			text: 'lossOfIntegrityText',
			choices: [
				'NA',
				'lossOfIntegrityChoice1',
				null,
				'lossOfIntegrityChoice2',
				null,
				'lossOfIntegrityChoice3',
				null,
				'lossOfIntegrityChoice4',
				null,
				'lossOfIntegrityChoice5'
			]
		},
		{
			id: 'loss_of_availability',
			text: 'lossOfAvailabilityText',
			choices: [
				'NA',
				'lossOfAvailabilityChoice1',
				null,
				null,
				null,
				'lossOfAvailabilityChoice2',
				null,
				'lossOfAvailabilityChoice3',
				null,
				'lossOfAvailabilityChoice4'
			]
		},
		{
			id: 'loss_of_accountability',
			text: 'lossOfAccountabilityText',
			choices: [
				'NA',
				'lossOfAccountabilityChoice1',
				null,
				null,
				null,
				null,
				null,
				'lossOfAccountabilityChoice2',
				null,
				'lossOfAccountabilityChoice3'
			]
		}
	]
};

const round_precision = Math.pow(10, 3);

export function average(data: number[]) {
	let res = 0;
	for (const value of data) {
		res += value;
	}
	return Math.round((res / data.length) * round_precision) / round_precision;
}
