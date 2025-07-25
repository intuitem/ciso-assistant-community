import { expect, type Locator, type Page } from './test-utils.js';

export enum FormFieldType {
	CHECKBOX = 'checkbox',
	DATE = 'date',
	FILE = 'file',
	SELECT = 'select',
	SELECT_AUTOCOMPLETE = 'select-autocomplete',
	SELECT_MULTIPLE_AUTOCOMPLETE = 'select-multi-autocomplete',
	TEXT = 'text',
	NUMBER = 'number'
}

type FormField = {
	locator: Locator;
	type: FormFieldType;
};

export class FormContent {
	readonly formTitle: Locator;
	readonly saveButton: Locator;
	readonly cancelButton: Locator;
	readonly fields: Map<string, FormField>;
	name: string | RegExp;

	constructor(
		public readonly page: Page,
		name: string | RegExp,
		fields: { name: string; type: FormFieldType }[]
	) {
		this.formTitle = this.page.getByTestId('modal-title');
		this.saveButton = this.page.getByTestId('save-button');
		this.cancelButton = this.page.getByTestId('cancel-button');
		this.name = name;
		this.fields = new Map(
			fields.map((field) => [
				field.name,
				{
					locator: this.page.getByTestId('form-input-' + field.name.replaceAll('_', '-')),
					type: field.type
				}
			])
		);
	}

	async fill(values: { [k: string]: any }) {
		for (const key in values) {
			const field = this.fields.get(key);

			switch (field?.type) {
				case FormFieldType.CHECKBOX:
					if (values[key]) {
						await field.locator.check();
					} else {
						await field.locator.uncheck();
					}
					break;
				case FormFieldType.FILE:
					await field.locator.setInputFiles(values[key]);
					break;
				case FormFieldType.SELECT:
					await field.locator.selectOption(values[key]);
					break;
				case FormFieldType.SELECT_AUTOCOMPLETE:
					if (
						(await field.locator.getByRole('option').isVisible()) &&
						(await field.locator
							.getByRole('searchbox')
							.evaluate((el) => el.classList.contains('disabled')))
					) {
						await expect(field.locator.getByRole('option')).toContainText(values[key]);
					} else {
						await field.locator.click();
						if (typeof values[key] === 'object' && 'request' in values[key]) {
							const responsePromise = this.page.waitForResponse(
								(resp) => resp.url().includes(values[key].request.url) && resp.status() === 200
							);
							await expect(
								field.locator.getByRole('option', { name: values[key].value }).first()
							).toBeVisible();
							await field.locator.getByRole('option', { name: values[key].value }).first().click();

							await responsePromise;
						} else {
							await expect(
								field.locator.getByRole('option', { name: values[key] }).first()
							).toBeVisible();
							await field.locator.getByRole('option', { name: values[key] }).first().click();
						}
					}
					break;
				case FormFieldType.SELECT_MULTIPLE_AUTOCOMPLETE:
					await field.locator.click();
					for (const val of values[key]) {
						await expect(field.locator.getByRole('option', { name: val }).first()).toBeVisible();
						await field.locator.getByRole('option', { name: val }).first().click();
					}
					if (
						(await field.locator.isEnabled()) &&
						!(await field.locator
							.getByRole('searchbox')
							.evaluate((el) => el.classList.contains('disabled')))
					) {
						await field.locator.press('Escape');
					}
					break;
				case FormFieldType.DATE:
					await field.locator.clear();
				case FormFieldType.NUMBER:
					await field?.locator.fill(values[key].toString());
					break;
				default:
					await field?.locator.fill(values[key]);
					break;
			}
		}
	}

	async hasTitle() {
		await expect(this.formTitle).toBeVisible();
		// await expect(this.formTitle).toHaveText(this.name);
	}
}
