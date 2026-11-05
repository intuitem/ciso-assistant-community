export interface ExperimentalEntry {
	title: string;
	desc: string;
	link: string;
	tags: string[];
}

/** Experiments whose routes only exist in an edition that overlays this file.
 * Kept as a data module so the index page itself is never duplicated. */
export const experimentalExtras: ExperimentalEntry[] = [];
