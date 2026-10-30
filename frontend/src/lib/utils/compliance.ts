/**
 * Compliance % convention: (compliant + ½ partially compliant) over the assessed,
 * applicable requirements. Not applicable and not assessed stay out of the
 * denominator; progress is reported separately. Null when nothing is assessed.
 */
export function compliancePercent(
	compliant: number,
	partiallyCompliant: number,
	nonCompliant: number
): number | null {
	const assessed = compliant + partiallyCompliant + nonCompliant;
	return assessed ? ((compliant + 0.5 * partiallyCompliant) / assessed) * 100 : null;
}
