import { expect, type Locator, type Page } from './test-utils';

export enum FormFieldType {
	CHECKBOX = 'checkbox',
	FILE = 'file',
	SELECT = 'select',
	SELECT_AUTOCOMPLETE = 'select-auto-complete',
	TEXT = 'text'
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
					locator: this.page.getByTestId('form-input-' + field.name.replace('_', '-')),
					type: field.type
				}
			])
		);
	}

	async fill(values: { [k: string]: string }) {
		for (const key in values) {
			const field = this.fields.get(key);
			switch (field?.type) {
				case FormFieldType.CHECKBOX:
					if (values[key] === 'true') {
						await field.locator.check();
					} else if (values[key] === 'false') {
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
					await field.locator.click();
					await expect(this.page.locator('li', { hasText: values[key] })).toBeVisible();
					await this.page.locator('li', { hasText: values[key] }).click();
					break;
				default:
					await field?.locator.fill(values[key]);
					break;
			}
		}
	}

	async hasTitle() {
		await expect(this.formTitle).toBeVisible();
		await expect(this.formTitle).toHaveText(this.name);
	}
}
