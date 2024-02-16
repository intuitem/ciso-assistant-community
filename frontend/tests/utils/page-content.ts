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

    constructor(public readonly page: Page, url: string, name: string | RegExp, fields: {name: string, type: FormFieldType}[] = [{name: "name", type: FormFieldType.TEXT}, {name: "description", type: FormFieldType.TEXT}]) {
        super(page, url, name);
        this.form = typeof name == 'string' ? new FormContent(page, "New " + name.substring(0, name.length - 1), fields) : new FormContent(page, new RegExp(/New /.source + name.source), fields);
        this.itemDetail = new PageDetail(page, url, this.form, "");
        this.addButton = this.page.getByTestId("add-button");
        this.editButton = this.page.getByTestId("edit-button");
        this.searchInput = this.page.getByTestId("search-input");
        this.deleteModalTitle = this.page.getByTestId("modal-title");
        this.deleteModalConfirmButton = this.page.getByTestId("delete-confirm-button");
        this.deleteModalCancelButton = this.page.getByTestId("delete-cancel-button");
    }

    async hasTitle() {
        await expect.soft(this.pageTitle).toHaveText(this.name);
    }

    async createItem(values: { [k: string]: any }, dependency?: any) {
		if (dependency) {
			await this.page.goto('/libraries');
			await this.page.waitForURL('/libraries');

			await this.importLibrary(dependency.name, dependency.urn);
			await this.goto();
		}

        await this.addButton.click();
        await this.form.hasTitle();
        await this.form.fill(values);
        await this.form.saveButton.click();
        await expect(this.form.formTitle).not.toBeVisible();
        if (typeof this.name == 'string') {
            if (this.name === "Users") {
                await this.isToastVisible('User successfully created' + /\..+/.source);
            }
            else {
                await this.isToastVisible('Successfully created ' + this.name.substring(0, this.name.length - 1).toLowerCase() + /\..+/.source);
            }
        }
        else {
            await this.isToastVisible('Successfully created ' + this.name.source + /\..+/.source, 'i');
        }
    }

    async importLibrary(name: string, urn: string, language: string="English") {
        if (await this.tab('Imported libraries').isVisible()) {
            if (await this.getRow(name).isHidden()) {
                await this.tab('Libraries store').click();
                expect(this.tab('Libraries store').getAttribute('aria-selected')).toBeTruthy();
            } else {
                return;
            }
        }
        await this.importItemButton(name, language).click();
        await this.isToastVisible('Successfully imported library ' + urn + '.+', undefined, { timeout: 15000});
        await this.tab('Imported libraries').click();
        expect(this.tab('Imported libraries').getAttribute('aria-selected')).toBeTruthy();
        expect(this.getRow(name)).toBeVisible();
    }

    async viewItemDetail(value?: string) {
        if (value) {
            await this.getRow(value).getByTestId("tablerow-detail-button").click();
            this.itemDetail.setItem(value);
        } else {
            await this.getRow().getByTestId("tablerow-detail-button").click();
            this.itemDetail.setItem(await this.getRow().innerText());
        }
        await this.page.waitForURL(new RegExp("^.*\\" + this.url + "\/.+"));
    }

    async waitUntilLoaded() {
        if (await this.getRow("loading").first().isVisible()) {
            await this.getRow("loading").first().waitFor({state: 'hidden'});
        }
    }

    getRow(value?: string, additional?: any) {
        return value ? additional ? this.page.getByRole('row', { name: value }).filter({ has: this.page.getByText(additional).first() }) : this.page.getByRole('row', { name: value }) : this.page.getByRole('row').first();
    }

    collumnHeader(value: string) {
        return this.page.getByTestId("tableheader").filter({ hasText: value });
    }

    tab(value: string) {
        return this.page.getByTestId('tab').filter({ hasText: value });
    }

    editItemButton(value: string) {
        return this.getRow(value).getByTestId("tablerow-edit-button");
    }

    deleteItemButton(value: string) {
        return this.getRow(value).getByTestId("tablerow-delete-button");
    }

    importItemButton(value: string, language?: string) {
        return language ? this.getRow(value, language).getByTestId("tablerow-import-button") : this.getRow(value).getByTestId("tablerow-import-button").first();
    }
}