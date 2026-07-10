export const CALENDAR_CATEGORIES = {
	appliedControl: {
		label: 'appliedControls',
		dotClass: 'bg-violet-500',
		borderClass: 'border-l-violet-500',
		bgClass: 'bg-violet-50',
		hoverClass: 'hover:bg-violet-100',
		textClass: 'text-violet-700'
	},
	riskAcceptance: {
		label: 'riskAcceptances',
		dotClass: 'bg-green-500',
		borderClass: 'border-l-green-500',
		bgClass: 'bg-green-50',
		hoverClass: 'hover:bg-green-100',
		textClass: 'text-green-700'
	},
	audit: {
		label: 'complianceAssessments',
		dotClass: 'bg-yellow-500',
		borderClass: 'border-l-yellow-500',
		bgClass: 'bg-yellow-50',
		hoverClass: 'hover:bg-yellow-100',
		textClass: 'text-yellow-700'
	},
	task: {
		label: 'tasks',
		dotClass: 'bg-primary-500',
		borderClass: 'border-l-primary-500',
		bgClass: 'bg-primary-50',
		hoverClass: 'hover:bg-primary-100',
		textClass: 'text-primary-700'
	},
	contract: {
		label: 'contracts',
		dotClass: 'bg-teal-500',
		borderClass: 'border-l-teal-500',
		bgClass: 'bg-teal-50',
		hoverClass: 'hover:bg-teal-100',
		textClass: 'text-teal-700'
	},
	securityException: {
		label: 'securityExceptions',
		dotClass: 'bg-red-500',
		borderClass: 'border-l-red-500',
		bgClass: 'bg-red-50',
		hoverClass: 'hover:bg-red-100',
		textClass: 'text-red-700'
	},
	finding: {
		label: 'findings',
		dotClass: 'bg-pink-500',
		borderClass: 'border-l-pink-500',
		bgClass: 'bg-pink-50',
		hoverClass: 'hover:bg-pink-100',
		textClass: 'text-pink-700'
	},
	riskAssessment: {
		label: 'riskAssessments',
		dotClass: 'bg-sky-500',
		borderClass: 'border-l-sky-500',
		bgClass: 'bg-sky-50',
		hoverClass: 'hover:bg-sky-100',
		textClass: 'text-sky-700'
	}
} as const;

export type CalendarCategory = keyof typeof CALENDAR_CATEGORIES;
export type CalendarCategoryConfig = (typeof CALENDAR_CATEGORIES)[CalendarCategory];

export interface CalendarEvent {
	label: string;
	date: Date;
	link: string;
	users: any[];
	category: CalendarCategory;
	status?: string;
}
