export interface TableSource {
	/** Field-name → label map (e.g. `{ name: 'name' }`); build with `headData(model)`, not a label array. */
	head: Record<string, string>;
	/** The formatted table body values. */
	body: any;
	/** The data returned when an interactive row is clicked. */
	meta?: any;
	/** The formatted table footer values. */
	foot?: string[];
	/** The table filters. It can be used if the URLModel is not in listViewFields (table.ts) */
	filters?: any;
}
