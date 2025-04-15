import { Element } from '../core/element';

export class ModelTable extends Element {
	static DATA_TESTID = 'model-table';
	_columnNames: string[] | null;

	constructor(...args: Element.Args) {
		super(...args);
		this._columnNames = null;
	}

	/**
	 * Gets a specific row from the table
	 * @param index The row index to retrieve
	 * @returns The row element
	 * @todo Implement this method
	 */
	getRow(index?: number) {
		// TODO: Implement row retrieval logic
		throw new Error('Method not implemented');
	}
}
