import type { Locale } from '$lib/utils/locales';
import { getCookie } from '$lib/utils/cookies';
import { browser } from '$app/environment';

const dateFormatLocales: Record<Locale, string> = {
	fr: 'fr-FR',
	en: 'en-US',
	ar: 'ar-SA',
	pt: 'pt-PT',
	es: 'es-ES',
	nl: 'nl-NL',
	de: 'de-DE',
	it: 'it-IT',
	pl: 'pl-PL',
	ro: 'ro-RO',
	hi: 'hi-IN',
	ur: 'ur-PK',
	cs: 'cs-CZ',
	sv: 'sv-SE',
	id: 'id-ID',
	da: 'da-DK',
	hu: 'hu-HU',
	uk: 'uk-UA',
	el: 'el-GR',
	tr: 'tr-TR',
	hr: 'hr-HR',
	zh: 'zh-CN',
	lt: 'lt-LT'
};

export function formatDateOrDateTime(isoString: string, locale: Locale | null = null): string {
	if (typeof isoString !== 'string') {
		return isoString;
	}

	if (locale === null) {
		if (browser) {
			locale = (getCookie('LOCALE') as Locale) ?? null;
		}
	}
	locale ??= 'en';

	const dateFormatLocale = dateFormatLocales[locale] ?? 'en-US';
	const date = new Date(isoString);

	const hasTime = isoString.includes('T');

	if (hasTime) {
		return date.toLocaleString(dateFormatLocale);
	} else {
		return date.toLocaleDateString(dateFormatLocale);
	}
}
