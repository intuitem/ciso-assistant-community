import { describe, it, expect, afterAll, afterEach } from 'vitest';

import { baseLocale, overwriteGetLocale } from '$paraglide/runtime';
import { safeTranslate, setUseRiskCategoryLabel, translateChoiceLabel } from './i18n';

describe('use_risk_category_label wording swap', () => {
	afterEach(() => {
		setUseRiskCategoryLabel(false);
	});

	it('translates qualification keys normally by default', () => {
		expect(safeTranslate('qualifications')).toBe('Qualifications');
		expect(safeTranslate('qualification')).toBe('Qualification');
	});

	it('swaps qualification wording for risk category when enabled', () => {
		setUseRiskCategoryLabel(true);
		expect(safeTranslate('qualifications')).toBe('Risk categories');
		expect(safeTranslate('qualification')).toBe('Risk category');
		expect(safeTranslate('noQualificationsData')).toBe('No risk categories found on incidents');
	});

	it('leaves unrelated keys untouched when enabled', () => {
		setUseRiskCategoryLabel(true);
		expect(safeTranslate('threats')).toBe('Threats');
	});

	it('reverts to qualification wording when disabled again', () => {
		setUseRiskCategoryLabel(true);
		setUseRiskCategoryLabel(false);
		expect(safeTranslate('qualifications')).toBe('Qualifications');
	});
});

describe('translateChoiceLabel', () => {
	afterAll(() => {
		overwriteGetLocale(() => baseLocale);
	});

	it('prefers the key derived from the value over the one derived from the label', () => {
		// Both resolve; the value is the key tables and detail views use.
		expect(translateChoiceLabel('Other', 'privacy_other')).toBe('Other (Specify in Description)');
	});

	it('falls back to the label when the value has no message key', () => {
		expect(translateChoiceLabel('France', 'FR')).toBe('France');
	});

	it('falls back to the label for a non-string value', () => {
		expect(translateChoiceLabel('Critical', 1)).toBe('Critical');
	});

	it('returns the label untouched when neither has a message key', () => {
		expect(translateChoiceLabel('Acme Corp', 'b3f1c0de-0000-4000-8000-000000000000')).toBe(
			'Acme Corp'
		);
	});

	it('translates privacy choices, whose keys follow the value and not the label', () => {
		overwriteGetLocale(() => 'nl');
		// SUP-1796: the English label from the choice endpoint has no message
		// key, so a label-only lookup left these dropdowns untranslated.
		expect(translateChoiceLabel('Unauthorized Disclosure', 'privacy_unauthorized_disclosure')).toBe(
			'Ongeoorloofde openbaarmaking'
		);
		expect(translateChoiceLabel('Destruction', 'privacy_destruction')).toBe('Vernietiging');
		expect(translateChoiceLabel('Authority Notified', 'privacy_authority_notified')).toBe(
			'Autoriteit geïnformeerd'
		);
	});
});
