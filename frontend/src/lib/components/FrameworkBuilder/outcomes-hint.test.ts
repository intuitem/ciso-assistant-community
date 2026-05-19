import { describe, expect, test } from 'vitest';
import { locales, setLocale } from '$paraglide/runtime';
import { m } from '$paraglide/messages';

// `OutcomesEditor.svelte` renders the CEL `"true"` literal as a real <code>
// element by splitting `builderOutcomeRulesHint` on a NUL sentinel substituted
// for the `{trueLiteral}` placeholder. If any locale drops the placeholder, the
// split returns one chunk and the <code> element renders glued to the sentence
// end instead of in place. Paraglide does NOT fail the build on missing
// placeholders, so guard the contract here.
describe('builderOutcomeRulesHint placeholder contract', () => {
	for (const locale of locales) {
		test(`${locale} preserves {trueLiteral}`, () => {
			setLocale(locale, { reload: false });
			const rendered = m.builderOutcomeRulesHint({ trueLiteral: '__SENTINEL__' });
			expect(rendered).toContain('__SENTINEL__');
		});
	}
});
