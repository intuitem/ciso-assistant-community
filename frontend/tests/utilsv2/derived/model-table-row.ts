import { Element } from '../core/element';
import { DetailViewPage } from '../base/detail-view-page';
import type { Expect } from '../../utilsv2/core/base';
import type { Locator } from '@playwright/test';

/** Represents a row of the `<ModelTable/>`. */
export class ModelTableRow extends Element {
	static DATA_TESTID = 'model-table-row-elem';
	protected _deleteButton: Locator;
	protected _importButton: Locator;
	protected _tableDataElems: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._deleteButton = this._self.getByTestId('tablerow-delete-button');
		this._importButton = this._self.getByTestId('tablerow-import-button');
		this._tableDataElems = this._self.locator('td');
	}

	// This function could have a lot better UX by using the context of the ModelTable Element  instance to pass the column names to this function.
	async checkValue(expect: Expect, columnIndex: number, value: string) {
		const valueElem = this._tableDataElems.nth(columnIndex);
		await expect(valueElem).toBeVisible();
		await expect(valueElem).toHaveText(value);
	}

	/**
	 * Navigates to the detail view by clicking the current row.
	 * Requires `expect` to assert that the `data-href` attribute is present.
	 */
	async gotoDetailView(expect: Expect): Promise<DetailViewPage> {
		const detailButton = await this._self.getByTestId('tablerow-detail-button');
		const detailViewHref = await detailButton.getAttribute('href');
		expect(detailViewHref).not.toBeNull();
		await this.getSelf().click();
		// The class passed to this._goto must be either DetailViewPage or DetailViewPage derived class.
		// The choice of the class must be based on the context of the element.
		return this._goto(DetailViewPage, detailViewHref as string);
	}

	/**
	 * Load the library represented by the row.
	 * This method will not work if there is no library load button on the row.
	 */
	async doLoadLibrary(existsOk: boolean = false): Promise<void> {
		if (existsOk) {
			const isVisible = await this._importButton.isVisible();
			if (!isVisible) return;
		}
		await this._importButton.click();
	}

	/**
	 * Deletes the object represented by the row.
	 * This method clicks the row's delete button, then confirms the deletion
	 * by clicking the submit button in the confirmation modal.
	 */
	async doDeleteObject(): Promise<void> {
		await this._deleteButton.click();

		if (this._getContext('URLModel') === 'folders') {
			// Accessing an element outside the ModelTableRow HTML Body violates the Element Access Rules, but it's ok to do so when dealing with modals.
			const deleteConfirmInput = this._getPage()
				.getSelf()
				.getByTestId('delete-prompt-confirm-textfield');
			const deleteConfirmButton = this._getPage()
				.getSelf()
				.getByTestId('delete-prompt-confirm-button');

			await deleteConfirmInput.fill('yes');
			await deleteConfirmButton.click();
		} else {
			// There seem to be multiple delete-confirm-button, from what i've seen the last one is always the one displayed at the screen.
			const deleteConfirmButton = this._getPage()
				.getSelf()
				.getByTestId('delete-confirm-button')
				.last();
			await deleteConfirmButton.click();
		}
	}
}
