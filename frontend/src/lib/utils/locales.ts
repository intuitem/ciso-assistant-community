import * as m from '../../paraglide/messages';

export const LOCALE_MAP = {
	en: {
		name: 'english',
		flag: '🇬🇧'
	},
	fr: {
		name: 'french',
		flag: '🇫🇷'
	},
	de: {
		name: 'german',
		flag: '🇩🇪'
	},
	ar: {
		name: 'arabic',
		flag: '🇸🇦'
	},
	pt: {
		name: 'portuguese',
		flag: '🇧🇷'
	},
	es: {
		name: 'spanish',
		flag: '🇪🇸'
	},
	nl: {
		name: 'dutch',
		flag: '🇳🇱'
	},
	it: {
		name: 'italian',
		flag: '🇮🇹'
	},
	pl: {
		name: 'polish',
		flag: '🇵🇱'
	},
	ro: {
		name: 'romanian',
		flag: '🇷🇴'
	},
	hi: {
		name: 'hindi'
	},
	ur: {
		name: 'urdu'
	},
	cs: {
		name: 'czech',
		flag: '🇨🇿'
	},
	sv: {
		name: 'swedish',
		flag: '🇸🇪'
	},
	id: {
		name: 'indonesian',
		flag: '🇮🇩'
	},
	da: {
		name: 'danish',
		flag: '🇩🇰'
	},
	hu: {
		name: 'hungarian',
		flag: '🇭🇺'
	},
	uk: {
		name: 'ukrainian',
		flag: '🇺🇦'
	},
	el: {
		name: 'greek',
		flag: '🇬🇷'
	},
	tr: {
		name: 'turkish',
		flag: '🇹🇷'
	},
	hr: {
		name: 'croatian',
		flag: '🇭🇷'
	},
	zh: {
		name: 'chinese',
		flag: '🇨🇳'
	},
	lt: {
		name: 'lithuanian',
		flag: '🇱🇹'
	}
};

export const language: any = {
	french: m.french(),
	english: m.english(),
	arabic: m.arabic(),
	portuguese: m.portuguese(),
	spanish: m.spanish(),
	german: m.german(),
	dutch: m.dutch(),
	italian: m.italian(),
	polish: m.polish(),
	romanian: m.romanian(),
	hindi: m.hindi(),
	urdu: m.urdu(),
	czech: m.czech(),
	swedish: m.swedish(),
	indonesian: m.indonesian(),
	danish: m.danish(),
	hungarian: m.hungarian(),
	ukrainian: m.ukrainian(),
	greek: m.greek(),
	turkish: m.turkish(),
	croatian: m.croatian(),
	chinese: m.chinese(),
	lithuanian: m.lithuanian()
};

export const defaultLangLabels = {
	fr: 'Français',
	en: 'English',
	ar: 'العربية',
	pt: 'Português',
	es: 'Español',
	nl: 'Nederlands',
	de: 'Deutsch',
	it: 'Italiano',
	pl: 'Polski',
	ro: 'Română',
	hi: 'हिंदी',
	ur: 'اردو',
	cs: 'Český',
	sv: 'Svenska',
	id: 'Bahasa Indonesia',
	da: 'Dansk',
	hu: 'Magyar',
	uk: 'Українська',
	el: 'Ελληνικά',
	tr: 'Türkçe',
	hr: 'Hrvatski',
	zh: '简体中文',
	lt: 'Lietuvių'
} as const;

export type Locale = keyof typeof defaultLangLabels;

export function toCamelCase(str: string) {
	if (typeof str !== 'string') return str;
	str = str.charAt(0).toLowerCase() + str.slice(1);
	return str.replace(/[_-\s]\w/g, (match) => match.charAt(1).toUpperCase());
}
