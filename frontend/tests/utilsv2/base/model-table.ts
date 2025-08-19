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
	 * @returns The row element at index (first row by default)
	 * @todo Implement this method
	 */
	async getRow(index?: number) {
		const rows = await this._self.getByTestId('modeltable-body-row-elem').all();
		return rows.at(index ?? 0);
	}
}
