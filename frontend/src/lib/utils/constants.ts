import { env } from '$env/dynamic/public';

export const BASE_API_URL = `${
	env.hasOwnProperty('PUBLIC_BACKEND_API_URL')
		? env.PUBLIC_BACKEND_API_URL
		: 'http://localhost:8000/api'
}`;

export const BACKEND_API_EXPOSED_URL = `${
	env.hasOwnProperty('PUBLIC_BACKEND_API_EXPOSED_URL')
		? env.PUBLIC_BACKEND_API_EXPOSED_URL
		: BASE_API_URL
}`;

export const RISK_COLOR_PALETTE: string[] = ['#BBF7D0', '#BEF264', '#FEF08A', '#FBBF24', '#F87171'];

export const complianceResultColorMap = {
	not_assessed: '#d1d5db',
	partially_compliant: '#fde047',
	non_compliant: '#f87171',
	not_applicable: '#000000',
	compliant: '#86efac'
};

export const complianceStatusColorMap = {
	to_do: '#9ca3af',
	in_progress: '#f59e0b',
	in_review: '#3b82f6',
	done: '#86efac'
};

export const MONTH_LIST = [
	'January',
	'February',
	'March',
	'April',
	'May',
	'June',
	'July',
	'August',
	'September',
	'October',
	'November',
	'December'
];

export const TODAY = new Date();

export const UUID_REGEX = '([0-9a-f]{8}\\-[0-9a-f]{4}\\-[0-9a-f]{4}\\-[0-9a-f]{4}\\-[0-9a-f]{12})';
export const UUID_LIST_REGEX = new RegExp(`^${UUID_REGEX}(,${UUID_REGEX})*$`);

export const URN_REGEX =
	/^urn:([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)(?::([a-zA-Z0-9_-]+))?:([0-9A-Za-z\[\]\(\)\-\._:]+)$/;

export const LOCALE_DISPLAY_MAP = {
	en: '🇬🇧 English',
	fr: '🇫🇷 Français',
	de: '🇩🇪 Deutsch'
};

export const ISO_8601_REGEX =
	/^([+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24:?00)([.,]\d+(?!:))?)?(\17[0-5]\d([.,]\d+)?)?([zZ]|([+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$/;
