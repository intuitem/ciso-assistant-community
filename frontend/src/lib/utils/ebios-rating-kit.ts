import { safeTranslate } from '$lib/utils/i18n';
import type { RatingLevel } from '$lib/utils/ebios-quotation';

// Default levels are named by i18n keys; custom ones are shown as written (the
// backend already picked the viewer's translation from the matrix).
export function ratingLevelLabel(level?: RatingLevel): string {
	if (!level) return '';
	return level.default ? safeTranslate(level.name) : level.name;
}
