import { expect, type Locator, type Page } from './test-utils.js';
import { FormContent, FormFieldType } from './form-content.js';
import { BasePage } from './base-page.js';
import { PageDetail } from './page-detail.js';

export class PageContent extends BasePage {
	readonly form: FormContent;
	readonly itemDetail: PageDetail;
	readonly addButton: Locator;
	readonly editButton: Locator;
	readonly searchInput: Locator;
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
		this.form = new FormContent(page, this.getFormTitle(name), fields);
		this.itemDetail = new PageDetail(page, url, this.form, '');
		this.addButton = this.page.getByTestId('add-button');
		this.editButton = this.page.getByTestId('edit-button');
		this.searchInput = this.page.getByTestId('search-input');
		this.deleteModalTitle = this.page.getByTestId('modal-title');
		this.deleteModalConfirmButton = this.page.getByTestId('delete-confirm-button');
		this.deleteModalCancelButton = this.page.getByTestId('delete-cancel-button');
	}

	private getFormTitle(name: string | RegExp): string | RegExp {
		return typeof name === 'string' ? `New ${name.slice(0, -1)}` : new RegExp(`New ${name.source}`);
	}

	async createItem(
		values: Record<string, any>,
		dependency?: { name: string; urn: string }
	): Promise<void> {
		if (dependency) {
			await this.importDependency(dependency);
		}

		await this.addButton.click();
		await this.form.hasTitle();
		await this.form.fill(values);
		await this.form.saveButton.click();
		await expect(this.form.formTitle).not.toBeVisible();
		await this.expectSuccessToast();
	}

	private async importDependency(dependency: { name: string; urn: string }): Promise<void> {
		await this.page.goto('/libraries');
		await this.page.waitForURL('/libraries');
		await this.importLibrary(dependency.name, dependency.urn);
		await this.goto();
	}

	private async expectSuccessToast(): Promise<void> {
		const objectName =
			typeof this.name === 'string' ? this.name.slice(0, -1).toLowerCase() : this.name.source;
		await this.isToastVisible(
			`The ${objectName} object has been successfully created${/.+/.source}`,
			typeof this.name === 'string' ? undefined : 'i'
		);
	}

	async importLibrary(name: string, urn?: string, language = 'English'): Promise<void> {
		await this.searchInput.fill(name);
		if (await this.isLibraryAlreadyLoaded(name)) return;

		if (await this.importItemButton(name, language === 'any' ? undefined : language).isHidden()) {
			await this.switchToLoadedLibraries(name);
		} else {
			await this.performLibraryImport(name, language);
		}
	}

	private async isLibraryAlreadyLoaded(name: string): Promise<boolean> {
		if (await this.isLoadedLibrariesTabSelected()) {
			if (await this.getRow(name).isHidden()) {
				await this.tab('Libraries store').click();
				await expect(this.tab('Libraries store')).toHaveAttribute('aria-selected', 'true');
			} else {
				return true;
			}
		}
		return false;
	}

	private async isLoadedLibrariesTabSelected(): Promise<boolean> {
		return (
			(await this.tab('Loaded libraries').isVisible()) &&
			(await this.tab('Loaded libraries').getAttribute('aria-selected')) === 'true'
		);
	}

	private async switchToLoadedLibraries(name: string): Promise<void> {
		await this.tab('Loaded libraries').click();
		await expect(this.tab('Loaded libraries')).toHaveAttribute('aria-selected', 'true');
		await this.searchInput.fill(name);
		await expect(this.getRow(name)).toBeVisible();
	}

	private async performLibraryImport(name: string, language: string): Promise<void> {
		await this.importItemButton(name, language === 'any' ? undefined : language).click();
		await this.isToastVisible(`The library has been successfully loaded.+`, undefined, {
			timeout: 15000
		});
		await this.switchToLoadedLibraries(name);
	}

	async viewItemDetail(value?: string): Promise<void> {
		if (value) {
			await this.getRow(value).getByTestId('tablerow-detail-button').click();
			await this.itemDetail.setItem(value);
		} else {
			await this.getRow().getByTestId('tablerow-detail-button').click();
			await this.itemDetail.setItem(await this.getRow().innerText());
		}
		await this.page.waitForURL(new RegExp('^.*\\' + this.url + '/.+'));
	}

	getRow(value?: string, additional?: any): Locator {
		return value
			? additional
				? this.page
						.getByRole('row', { name: value })
						.filter({ has: this.page.getByText(additional).first() })
						.first()
				: this.page.getByRole('row', { name: value }).first()
			: this.page.getByRole('row').first();
	}

	collumnHeader(value: string): Locator {
		return this.page.getByTestId('tableheader').filter({ hasText: value });
	}

	tab(value: string): Locator {
		return this.page.getByTestId('tab').filter({ hasText: value });
	}

	editItemButton(value: string): Locator {
		return this.getRow(value).getByTestId('tablerow-edit-button');
	}

	deleteItemButton(value: string): Locator {
		return this.getRow(value).getByTestId('tablerow-delete-button');
	}

	importItemButton(value: string, language?: string): Locator {
		return language
			? this.getRow(value, language).getByTestId('tablerow-import-button')
			: this.getRow(value).getByTestId('tablerow-import-button');
	}
}
