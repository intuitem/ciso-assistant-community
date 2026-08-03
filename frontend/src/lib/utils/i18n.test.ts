import { describe, it, expect, afterEach } from 'vitest';

import { safeTranslate, setUseRiskCategoryLabel } from './i18n';

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
