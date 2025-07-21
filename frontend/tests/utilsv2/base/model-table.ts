import { Element } from '../core/element';
import { ModelTableRow } from '../derived/model-table-row';
import type { Locator, Expect } from '@playwright/test';

export class ModelTable extends Element {
	static DATA_TESTID = 'model-table';
	protected _searchInput: Locator;
	protected _filterButton: Locator;
	protected _columnNames: string[] | null;

	constructor(...args: Element.Args) {
		super(...args);
		this._searchInput = this._self.getByTestId('search-input-elem');
		this._filterButton = this._self.getByTestId('model-table-filter-button-elem');
		this._columnNames = null;
	}

	async checkIfSearchBarVisible(expect: Expect) {
		await expect(this._searchInput).toBeVisible();
	}

	/** Fills the search bar of the ModelTable with a string. */
	async doSearch(searchString: string) {
		await this._searchInput.fill(searchString);
	}

	/** Checks that the number of rows displayed in the ModelTable`. */
	async checkDisplayedRowCount(expect: Expect, numberOfRows: number) {
		await expect(this._self.getByTestId('model-table-row-elem')).toHaveCount(numberOfRows);
	}

	/** `[data-testid="model-table-row"]` Get the first row of the `<ModelTable/>`. */
	getFirstRow(): ModelTableRow {
		return this._getSubElement(ModelTableRow, {
			first: true
		});
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
