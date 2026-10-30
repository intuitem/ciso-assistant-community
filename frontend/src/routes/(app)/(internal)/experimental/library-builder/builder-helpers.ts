/** Helpers shared between the library-builder list and draft pages. */

/** Client-side mirror of backend urn_safe_leaf, restricted to the identity
 *  alphabet ([a-z0-9_-]) accepted for packager / ref_id. */
export function identitySlug(name: string): string {
	return name
		.toLowerCase()
		.normalize('NFKD')
		.replace(/[\u0300-\u036f]/g, '')
		.replace(/[^a-z0-9_-]+/g, '-')
		.replace(/^-+|-+$/g, '');
}

/** Starter 3×3 risk matrix. The single matrix of a library carries the
 *  library's own identity (bare family URN server-side). */
export function defaultMatrixObject(refId: string, name: string): Record<string, unknown> {
	const level = (abbreviation: string, levelName: string, hexcolor: string) => ({
		abbreviation,
		name: levelName,
		description: '',
		hexcolor
	});
	return {
		ref_id: refId,
		name,
		probability: [
			level('L', 'Low', '#BBF7D0'),
			level('M', 'Medium', '#FEF08A'),
			level('H', 'High', '#FECACA')
		],
		impact: [
			level('L', 'Low', '#BBF7D0'),
			level('M', 'Medium', '#FEF08A'),
			level('H', 'High', '#FECACA')
		],
		risk: [
			level('L', 'Low', '#22C55E'),
			level('M', 'Medium', '#F59E0B'),
			level('H', 'High', '#EF4444')
		],
		grid: [
			[0, 0, 1],
			[0, 1, 2],
			[1, 2, 2]
		]
	};
}
