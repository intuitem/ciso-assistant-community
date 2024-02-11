import { expect, type Locator, type Page } from './test-utils';
import { FormContent, FormFieldType } from './form-content';
import { BasePage } from './base-page';

export class PageContent extends BasePage {
	readonly form: FormContent;
	readonly addButton: Locator;
	readonly deleteModalTitle: Locator;
	readonly deleteModalConfirmButton: Locator;
	readonly deleteModalCancelButton: Locator;

	constructor(
		public readonly page: Page,
		url: string,
		name: string | RegExp,
		fields: { name: string; type: FormFieldType }[] = [
			{ name: 'name', type: FormFieldType.TEXT },
			{ name: 'description', type: FormFieldType.TEXT }
		]
	) {
		super(page, url, name);
		this.form =
			typeof name == 'string'
				? new FormContent(page, 'New ' + name.substring(0, name.length - 1), fields)
				: new FormContent(page, new RegExp(/New /.source + name.source), fields);
		this.addButton = this.page.getByTestId('add-button');
		this.deleteModalTitle = this.page.getByTestId('modal-title');
		this.deleteModalConfirmButton = this.page.getByTestId('delete-confirm-button');
		this.deleteModalCancelButton = this.page.getByTestId('delete-cancel-button');
	}

	async hasTitle() {
		await expect.soft(this.page.locator('#page-title')).toHaveText(this.name);
	}

	async createItem(values: { [k: string]: string }) {
		await this.addButton.click();
		await this.form.hasTitle();
		await this.form.fill(values);
		await this.form.saveButton.click();
		await expect(this.form.formTitle).not.toBeVisible();
		if (typeof this.name == 'string') {
			await expect(
				this.page.getByTestId('toast').filter({
					hasText: new RegExp(
						'Successfully created ' +
							this.url.substring(1, this.url.length - 1).replaceAll('-', ' ') +
							'.'
					)
				})
			).toBeVisible();
		} else {
			await expect(
				this.page
					.getByTestId('toast')
					.filter({ hasText: new RegExp('Successfully created ' + this.name.source + '.', 'i') })
			).toBeVisible();
		}
	}

	async importLibrary(name: string, urn: string) {
		await this.importItemButton(name).click();
		await expect(
			this.page
				.getByTestId('toast')
				.filter({ hasText: new RegExp('Successfully imported library ' + urn + '.') })
		).toBeVisible({ timeout: 15000 });
	}

	editItemButton(value: string) {
		return this.page.getByRole('row', { name: value }).getByTestId('tablerow-edit-button');
	}

	deleteItemButton(value: string) {
		return this.page.getByRole('row', { name: value }).getByTestId('tablerow-delete-button');
	}

	importItemButton(value: string) {
		return this.page.getByRole('row', { name: value }).getByTestId('tablerow-import-button');
	}
}
