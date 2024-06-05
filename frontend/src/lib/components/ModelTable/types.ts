export interface TableSource {
	/** The formatted table heading values. */
	head: any;
	/** The formatted table body values. */
	body: any;
	/** The data returned when an interactive row is clicked. */
	meta?: any;
	/** The formatted table footer values. */
	foot?: string[];
}
