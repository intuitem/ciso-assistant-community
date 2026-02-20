import { expect, type Locator, type Page } from './test-utils.js';
import { FormContent, FormFieldType } from './form-content.js';
import { BasePage } from './base-page.js';
import { PageDetail } from './page-detail.js';

interface Filter {
	has?: Locator | undefined;
	hasNot?: Locator;
	hasNotText?: string | RegExp;
	hasText?: string | RegExp;
	visible?: boolean;
}

export class PageContent extends BasePage {
	readonly form: FormContent;
	readonly itemDetail: PageDetail;
	readonly addButton: Locator;
	readonly importButton: Locator;
	readonly editButton: Locator;
	readonly searchInput: Locator;
	readonly deleteModalTitle: Locator;
	readonly deleteModalConfirmButton: Locator;
	readonly deleteModalCancelButton: Locator;
	readonly deleteModalPromptConfirmButton: Locator;
	readonly deleteModalPromptConfirmText: Locator;

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
		this.itemDetail = new PageDetail(page, url, this.form, '');
		this.addButton = this.page.getByTestId('add-button');
		this.importButton = this.page.getByTestId('import-button');
		this.editButton = this.page.getByTestId('edit-button');
		this.searchInput = this.page.getByRole('searchbox').first();
		this.deleteModalTitle = this.page.getByTestId('modal-title');
		this.deleteModalConfirmButton = this.page.getByTestId('delete-confirm-button');
		this.deleteModalCancelButton = this.page.getByTestId('delete-cancel-button');
		this.deleteModalPromptConfirmButton = this.page.getByTestId('delete-prompt-confirm-button');
		this.deleteModalPromptConfirmText = this.page.getByTestId('delete-prompt-confirm-text');
	}

	async createItem(
		values: { [k: string]: any },
		dependency?: any,
		page?: Page,
		addButtonValue?: string
	) {
		if (dependency) {
			await this.page.goto('/libraries');
			await this.page.waitForURL('/libraries');

			await this.importLibrary(dependency.name, dependency.urn);
			await this.goto();
		}

		// Default to the first add button if no value is provided
		// addButtonValue is useful when there is multiple tabs with add buttons
		if (addButtonValue === undefined) {
			await this.addButton.first().click();
		} else {
			await this.addButton.filter({ hasText: addButtonValue }).click();
		}
		await this.form.hasTitle();
		if (page) {
			await page.waitForLoadState('networkidle');
		}

		await this.form.fill(values);

		// If parent_folder field is visible and enabled (enterprise edition) and not already provided, fill it with 'Global'
		const parentFolderField = this.page.getByTestId('form-input-parent-folder');
		if (
			!values.parent_folder &&
			(await parentFolderField.isVisible({ timeout: 1000 }).catch(() => false))
		) {
			const isDisabled = await parentFolderField
				.locator('.disabled')
				.first()
				.isVisible()
				.catch(() => false);
			if (!isDisabled) {
				await parentFolderField.click();
				await parentFolderField.getByRole('option', { name: 'Global' }).first().click();
			}
		}

		await this.form.saveButton.click();
		await expect(this.form.formTitle).not.toBeVisible();
		if (typeof this.name == 'string') {
			await this.isToastVisible(
				'The ' +
					this.name.substring(0, this.name.length - 1).toLowerCase() +
					' object has been successfully created' +
					/.+/.source
			);
		} else {
			await this.isToastVisible(
				'The ' + this.name.source + ' object has been successfully created' + /.+/.source,
				'i'
			);
		}
	}

	async importLibrary(name: string, urn?: string, language = 'English') {
		await this.page.waitForTimeout(3000);
		await this.page.getByRole('searchbox').first().clear();
		await this.page.getByRole('searchbox').first().fill(name);
		await this.page.waitForTimeout(3000);

		const filters = [
			{ has: this.page.getByText(name, { exact: true }).first() },
			{ has: this.page.getByText(language).first() }
		];
		const row = this.getRow(name, filters);

		const isAlreadyLoaded = await row.getByTestId('tablerow-import-button').isHidden();
		if (isAlreadyLoaded) return;

		const importButton = row.getByTestId('tablerow-import-button');
		await importButton.click();

		await this.isToastVisible(`The library has been successfully loaded.+`, undefined, {
			timeout: 15000
		});
	}

	async viewItemDetail(value?: string) {
		if (value) {
			await this.getRow(value).getByTestId('tablerow-detail-button').click();
			this.itemDetail.setItem(value);
		} else {
			await this.getRow().getByTestId('tablerow-detail-button').click();
			this.itemDetail.setItem(await this.getRow().innerText());
		}
		await this.page.waitForURL(new RegExp('^.*\\' + this.url + '/.+'));
	}

	/**
	 * Get the first table row that matches the given substring and optional filters
	 *
	 * @param substring Substring to look for within the row (case-insensitive search).
	 * @param filters Extra filters passed to the locator with the `locator.filter` method.
	 * @returns The first matching row.
	 */
	getRow(substring?: string, filters: Filter[] = []): Locator {
		const substringSearch = { name: substring };
		let rowLocator = this.page.getByRole('row', substringSearch);

		for (const filterOptions of filters) {
			rowLocator = rowLocator.filter(filterOptions);
		}

		const firstMatchingFound = rowLocator.first();
		return firstMatchingFound;
	}

	collumnHeader(value: string) {
		return this.page.getByTestId('tableheader').filter({ hasText: value });
	}

	tab(value: string) {
		return this.page.getByTestId('tabs-control').filter({ hasText: value });
	}

	editItemButton(value: string) {
		return this.getRow(value).getByTestId('tablerow-edit-button');
	}

	deleteItemButton(value: string) {
		return this.getRow(value).getByTestId('tablerow-delete-button');
	}

	deletePromptConfirmTextField() {
		return this.page.getByTestId('delete-prompt-confirm-textfield');
	}

	deletePromptConfirmButton() {
		return this.page.getByTestId('delete-prompt-confirm-button');
	}
}
