export const forms = {
	threat_agent: [
		{
			id: 'skill_level',
			text: 'How technically skilled is this group of threat agents?',
			choices: [
				'N/A',
				'No technical skills',
				null,
				'Some technical skills',
				null,
				'Advanced computer user',
				'Network and programming skills',
				null,
				null,
				'Security penetration skills'
			]
		},
		{
			id: 'motive',
			text: 'How motivated is this group of threat agents to find and exploit this vulnerability?',
			choices: [
				'N/A',
				'Low or no reward',
				null,
				null,
				'Possible reward',
				null,
				null,
				null,
				null,
				'High reward'
			]
		},
		{
			id: 'opportunity',
			text: 'What resources and opportunities are required for this group of threat agents to find and exploit this vulnerability?',
			choices: [
				'Full access or expensive resources required',
				null,
				null,
				null,
				'Special access or resources required',
				null,
				null,
				'Some access or resources required',
				null,
				'No access or resources required'
			]
		},
		{
			id: 'size',
			text: 'How large is this group of threat agents?',
			choices: [
				'N/A',
				null,
				'Developers or system administrators',
				null,
				'Intranet users',
				'Partners',
				'Authenticated users',
				null,
				null,
				'Anonymous Internet users'
			]
		}
	],
	business_impact: [
		{
			id: 'ease_of_discovery',
			text: 'How easy is it for this group of threat agents to discover this vulnerability?',
			choices: [
				'N/A',
				'Practically impossible',
				null,
				'Difficult',
				null,
				null,
				null,
				'Easy',
				null,
				'Automated tools available'
			]
		},
		{
			id: 'ease_of_exploit',
			text: 'How easy is it for this group of threat agents to actually exploit this vulnerability?',
			choices: [
				'N/A',
				'Theoretical',
				null,
				'Difficult',
				null,
				'Easy',
				null,
				null,
				null,
				'Automated tools available'
			]
		},
		{
			id: 'awareness',
			text: 'How well known is this vulnerability to this group of threat agents?',
			choices: [
				'N/A',
				'Unknown',
				null,
				null,
				'Hidden',
				null,
				'Obvious',
				null,
				null,
				'Public knowledge'
			]
		},
		{
			id: 'intrusion_detection',
			text: 'How likely is an exploit to be detected?',
			choices: [
				'N/A',
				'Active detection in application',
				null,
				'Logged and reviewed',
				null,
				null,
				null,
				null,
				'Logged without review',
				'Not logged'
			]
		}
	],
	vulnerability: [
		{
			id: 'financial_damage',
			text: 'How much financial damage will result from an exploit?',
			choices: [
				'N/A',
				'Less than the cost to fix the vulnerability',
				null,
				'Minor effect on annual profit',
				null,
				null,
				null,
				'Significant effect on annual profit',
				null,
				'Bankruptcy'
			]
		},
		{
			id: 'reputation_damage',
			text: 'Would an exploit result in reputation damage that would harm the business?',
			choices: [
				'N/A',
				'Minimal damage',
				null,
				null,
				'Loss of major accounts',
				'Loss of goodwill',
				null,
				null,
				null,
				'Brand damage'
			]
		},
		{
			id: 'non_compliance',
			text: 'How much exposure does non-compliance introduce?',
			choices: [
				'N/A',
				null,
				'Minor violation',
				null,
				null,
				'Clear violation',
				null,
				'High profile violation',
				null,
				null
			]
		},
		{
			id: 'privacy_violation',
			text: 'How much personally identifiable information could be disclosed?',
			choices: [
				'N/A',
				null,
				null,
				'One individual',
				null,
				'Hundreds of people',
				null,
				'Thousands of people',
				null,
				'Millions of people'
			]
		}
	],
	technical_impact: [
		{
			id: 'loss_of_confidentiality',
			text: 'How much data could be disclosed and how sensitive is it?',
			choices: [
				'N/A',
				null,
				'Minimal non-sensitive data disclosed',
				null,
				null,
				null,
				'Minimal critical data or extensive non-sensitive data disclosed',
				'Extensive critical data disclosed',
				null,
				'All data disclosed'
			]
		},
		{
			id: 'loss_of_integrity',
			text: 'How much data could be corrupted and how damaged is it?',
			choices: [
				'N/A',
				'Minimal slightly corrupt data',
				null,
				'Minimal seriously corrupt data',
				null,
				'Extensive slightly corrupt data',
				null,
				'Extensive seriously corrupt data',
				null,
				'All data totally corrupt'
			]
		},
		{
			id: 'loss_of_availability',
			text: 'How much service could be lost and how vital is it?',
			choices: [
				'N/A',
				'Minimal secondary services interrupted',
				null,
				null,
				null,
				'Minimal primary or extensive secondary services interrupted',
				null,
				'Extensive primary services interrupted',
				null,
				'All services completely lost'
			]
		},
		{
			id: 'loss_of_accountability',
			text: "Are the threat agents' actions traceable to an individual?",
			choices: [
				'N/A',
				'Fully traceable',
				null,
				null,
				null,
				null,
				null,
				'Possibly traceable',
				null,
				'Completely anonymous'
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
