import { describe, expect, it } from 'vitest';
import { contentDispositionHeader, parseContentDispositionFilename } from './contentDisposition';

// SUP-1791: an evidence uploaded as "Procédure de gestion.pdf" reached the backend as
// "Proc%C3%A9dure%20de%20gestion.pdf" and was stored under that literal name.
const ACCENTED = 'Procédure de gestion.pdf';

describe('contentDispositionHeader', () => {
	it('carries the real name in filename* and a Latin-1-safe fallback', () => {
		const header = contentDispositionHeader(ACCENTED);
		expect(header).toContain("filename*=utf-8''Proc%C3%A9dure%20de%20gestion.pdf");
		expect(header).toContain('filename="Proc-dure de gestion.pdf"');
		// The header is set on a fetch Request, which rejects anything outside Latin-1.
		expect(() => new Headers({ 'Content-Disposition': header })).not.toThrow();
	});

	it('defuses characters that would break out of the quoted-string', () => {
		const header = contentDispositionHeader('a";drop.pdf');
		expect(header).toContain('filename="a--drop.pdf"');
	});
});

describe('parseContentDispositionFilename', () => {
	it('round-trips what contentDispositionHeader emits', () => {
		expect(parseContentDispositionFilename(contentDispositionHeader(ACCENTED))).toBe(ACCENTED);
	});

	it('prefers filename* over the lossy ASCII fallback', () => {
		const header = `attachment; filename="Proc-dure.pdf"; filename*=utf-8''Proc%C3%A9dure.pdf`;
		expect(parseContentDispositionFilename(header)).toBe('Procédure.pdf');
	});

	it('falls back to a plain quoted filename', () => {
		expect(parseContentDispositionFilename('attachment; filename="report.pdf"')).toBe('report.pdf');
	});

	it('handles an unquoted filename', () => {
		expect(parseContentDispositionFilename('attachment; filename=report.pdf')).toBe('report.pdf');
	});

	it('falls back rather than throwing on a malformed escape', () => {
		const header = `attachment; filename="report.pdf"; filename*=utf-8''bad%ZZ.pdf`;
		expect(parseContentDispositionFilename(header)).toBe('report.pdf');
	});

	it('returns null when there is no filename at all', () => {
		expect(parseContentDispositionFilename('attachment')).toBeNull();
	});
});
