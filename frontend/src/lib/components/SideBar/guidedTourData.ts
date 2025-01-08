// id is not needed, just to help us with authoring
export const steps = [
	{
		id: 1,
		element: 'none',
		popover: {
			title: 'Welcome !',
			description:
				'The quick guided tour will help setup the main parts to get started with CISO Assistant.'
		}
	},
	{
		id: 2,
		element: '#organization',
		popover: {
			title: 'Click to unfold'
		}
	},
	{
		id: 3,
		element: '#domains',
		popover: {
			title: 'Click here',
			description: 'You will need to create a first domain to get started'
		}
	},
	{
		id: 4,
		element: '#add-button',
		popover: {
			description: 'You will need to create a first domain to get started'
		}
	},
	{
		id: 6,
		element: '#catalog',
		popover: {
			title: 'Click to unfold',
			description:
				'The library of CISO Assistant is quite comprehensive and contain multiple objects: frameworks, threats, matrices.'
		}
	},
	{ id: 7, element: '#frameworks', popover: { title: 'click here' } },
	{
		id: 8,
		element: '#add-button',
		popover: { title: 'Click to import one', description: 'Description' }
	},
	{
		id: 9,
		element: '#search-input',
		popover: { title: 'Type to filter', description: 'You can try csf v2' }
	},
	{
		id: 10,
		element: '#tablerow-import-button',
		popover: { title: 'Click here to load it' }
	},
	{
		id: 11,
		element: '#riskMatrices',
		popover: {
			title: 'click here',
			description:
				"You will also need a matrix for your risk assessment. Let's filter the library content to focus on that."
		}
	},
	{
		id: 12,
		element: '#add-button',
		popover: { title: 'Click to import one', description: 'Description' }
	},
	{
		id: 13,
		element: '#filters',
		popover: {
			description:
				'Notice that we came back to the library view with an extra filter being applied.'
		}
	},
	{
		id: 14,
		element: '#tablerow-import-button',
		popover: { title: 'Click here to load it' }
	},
	{ id: 15, element: '#compliance', popover: { title: 'Click to unfold' } },
	{
		id: 16,
		element: '#complianceAssessments',
		popover: {
			description:
				'This is where you can create and manage your audits that will serve as your baseline'
		}
	},
	{ id: 17, element: '#risk', popover: { title: 'Click to unfold' } },
	{
		id: 18,
		element: '#riskAssessments',
		popover: { description: 'And this is where you will be able to perform your risk assessments' }
	},
	{
		id: 19,
		element: '#sidebar-more-btn',
		popover: { description: 'You can retrigger the guided tour and adjust your preferences here.' }
	},
	{
		id: 20,
		element: 'none',
		popover: {
			title: 'All set',
			description:
				'You are good to go. Feel free to reach out the Discord server to interact with the growing community!'
		}
	}
];
