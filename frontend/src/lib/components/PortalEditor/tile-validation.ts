import { m } from '$paraglide/messages';

type Tile = { kind: string; target?: Record<string, any> };

/** What a tile needs before anyone can click it. `required` on the selects is
 *  decorative: the design saves as JSON, never as a native form submit. */
export function tileMissingField(item: Tile): string | null {
	const t = item.target ?? {};
	switch (item.kind) {
		case 'create':
		case 'navigate':
			return t.model ? null : m.model();
		case 'assessment':
			return t.framework ? null : m.framework();
		case 'quickForm':
			// Either wiring will do: a publication carries its own form.
			return t.publication || t.quick_form ? null : m.quickForm();
		case 'framework':
			return t.snapshot ? null : m.frameworkSnapshots();
		case 'certificationDocument':
			return (t.dest === 'document' ? t.token : t.url) ? null : m.proof();
		case 'external':
		case 'link':
			return t.url ? null : m.url();
		default:
			return null;
	}
}

export const tileIssue = (item: Tile): string | null => {
	const field = tileMissingField(item);
	return field ? m.portalTileMissing({ field }) : null;
};

export const countIncompleteTiles = (sections: { items?: Tile[] }[]): number =>
	sections.reduce(
		(n, s) => n + (s.items ?? []).filter((i) => tileMissingField(i) !== null).length,
		0
	);
