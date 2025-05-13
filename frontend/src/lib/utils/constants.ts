import { env } from '$env/dynamic/public';

export const BASE_API_URL = `${
	Object.hasOwn(env, 'PUBLIC_BACKEND_API_URL')
		? env.PUBLIC_BACKEND_API_URL
		: 'http://localhost:8000/api'
}`;

export const DEFAULT_LANGUAGE = `${
	Object.hasOwn(env, 'PUBLIC_DEFAULT_LANGUAGE') ? env.PUBLIC_DEFAULT_LANGUAGE : 'en'
}`;

export const ALLAUTH_API_URL = `${BASE_API_URL}/_allauth/app/v1`;

export const BACKEND_API_EXPOSED_URL = `${
	Object.hasOwn(env, 'PUBLIC_BACKEND_API_EXPOSED_URL')
		? env.PUBLIC_BACKEND_API_EXPOSED_URL
		: BASE_API_URL
}`;

export const complianceResultColorMap: { [key: string]: string } = {
	not_assessed: '#d1d5db',
	partially_compliant: '#fde047',
	non_compliant: '#f87171',
	not_applicable: '#000000',
	compliant: '#86efac'
};

export const complianceResultTailwindColorMap: { [key: string]: string } = {
	not_assessed: 'bg-gray-300',
	partially_compliant: 'bg-yellow-300',
	non_compliant: 'bg-red-300',
	not_applicable: 'bg-black text-white',
	compliant: 'bg-green-300'
};

export const complianceStatusColorMap: { [key: string]: string } = {
	to_do: '#9ca3af',
	in_progress: '#f59e0b',
	in_review: '#3b82f6',
	done: '#86efac'
};

export const complianceStatusTailwindColorMap = {
	to_do: 'bg-gray-400',
	in_progress: 'bg-amber-500',
	in_review: 'bg-blue-500',
	done: 'bg-green-300'
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
	de: '🇩🇪 Deutsch',
	es: '🇪🇸 Español',
	it: '🇮🇹 Italiano',
	nl: '🇳🇱 Nederlands',
	pt: '🇵🇹 Português',
	pl: '🇵🇱 Polski',
	ro: '🇷🇴 Română',
	ar: '🇸🇦 العربية',
	cs: '🇨🇿 Český',
	sv: '🇸🇪 Svenska',
	id: '🇮🇩 Bahasa Indonesia',
	da: '🇩🇰 Dansk'
};

export const ISO_8601_REGEX =
	/^([+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24:?00)([.,]\d+(?!:))?)?(\17[0-5]\d([.,]\d+)?)?([zZ]|([+-])([01]\d|2[0-3]):?([0-5]\d)?)?)?)?$/;

export const SECURITY_OBJECTIVE_SCALE_MAP = {
	'0-3': ['0', '1', '2', '3', '3'],
	'0-4': ['0', '1', '2', '3', '4'],
	'1-4': ['1', '2', '3', '4', '4'],
	'1-5': ['1', '2', '3', '4', '5'],
	'FIPS-199': ['low', 'moderate', 'moderate', 'high', 'high']
};
