import { expect, type Locator, type Page } from './test-utils.js';

export enum FormFieldType {
	CHECKBOX = 'checkbox',
	DATE = 'date',
	FILE = 'file',
	SELECT = 'select',
	SELECT_AUTOCOMPLETE = 'select-autocomplete',
	SELECT_MULTIPLE_AUTOCOMPLETE = 'select-multi-autocomplete',
	TEXT = 'text',
	NUMBER = 'number',
	DURATION = 'duration'
}

type FormField = {
	locator: Locator;
	type: FormFieldType;
};

/** Lazy selects surface options through server-side search on name/description.
 * Option labels compose scope and ref_id prefixes ("folder/ref_id - name"), so
 * strip them to type a fragment the backend search can actually match. */
const lazySearchText = (label: string): string =>
	String(label).split('/').pop()!.split(' - ').pop()!;

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

	// Options may render inside the field or, with portalDropdown, in a listbox portaled to <body>
	private optionLocator(field: FormField, name: string): Locator {
		return field.locator
			.getByRole('option', { name })
			.or(this.page.locator('ul.portaled-options:visible').getByRole('option', { name }))
			.first();
	}

	async fill(values: { [k: string]: any }) {
		const modal = this.page.getByTestId('modal-backdrop');
		if (await modal.isVisible({ timeout: 100 }).catch(() => false)) {
			const moreTrigger = modal
				.locator('[data-scope="accordion"][data-part="item-trigger"][data-state="closed"]')
				.first();
			if (await moreTrigger.isVisible({ timeout: 200 }).catch(() => false)) {
				await moreTrigger.click();
			}
		}
		for (const key in values) {
			const field = this.fields.get(key);
			for (const spinner of await this.page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 20_000
				});
			}

			if (field?.type === FormFieldType.TEXT) {
				const markdownEditBtn = this.page.getByTestId(`markdown-edit-btn-${key}`);
				if (await markdownEditBtn.isVisible()) {
					await markdownEditBtn.click();
				}
			}

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
					await expect(async () => {
						// count() doesn't wait: folder fields render a FolderTreeSelect with no
						// div.multiselect, and evaluate() would block on it until the toPass timeout.
						const multiselect = field.locator.locator('div.multiselect');
						const expected =
							values[key] !== null && typeof values[key] === 'object' && 'request' in values[key]
								? values[key].value
								: values[key];
						// Skip interaction when the field is disabled (auto-selected single option)
						// or already holds the value (preset via initialData): the expected entry
						// renders as a chip, not a dropdown option, so click-and-pick can't find it.
						if (
							(await multiselect.count()) > 0 &&
							(await multiselect.evaluate(
								(el, text) =>
									el.classList.contains('disabled') ||
									(el.querySelector('ul.selected')?.textContent ?? '').includes(text),
								expected
							))
						) {
							await expect(multiselect).toContainText(expected);
						} else {
							if (
								values[key] !== null &&
								typeof values[key] === 'object' &&
								'request' in values[key]
							) {
								const responsePromise = this.page.waitForResponse(
									(resp) => resp.url().includes(values[key].request.url) && resp.status() === 200
								);
								await field.locator.click();
								const optionLocator = this.optionLocator(field, values[key].value);
								// If the option isn't immediately visible, type to trigger lazy search
								if (!(await optionLocator.isVisible())) {
									await field.locator.getByRole('combobox').fill(lazySearchText(values[key].value));
								}
								await expect(optionLocator).toBeVisible({ timeout: 10_000 });
								await optionLocator.click();

								await responsePromise;
							} else {
								await field.locator.click();
								const optionLocator = this.optionLocator(field, values[key]);
								// If the option isn't immediately visible, type to trigger lazy search
								if (!(await optionLocator.isVisible())) {
									await field.locator.getByRole('combobox').fill(lazySearchText(values[key]));
								}
								await expect(optionLocator).toBeVisible({ timeout: 10_000 });
								await optionLocator.click();
							}
						}
					}).toPass({ timeout: 22_000, intervals: [500, 1000, 10_000] });
					break;
				case FormFieldType.SELECT_MULTIPLE_AUTOCOMPLETE: {
					const multiEl = field.locator.locator('div.multiselect');
					const isPreset = async (val: string) =>
						(await multiEl.count()) > 0 &&
						(await multiEl.evaluate(
							(el, text) => (el.querySelector('ul.selected')?.textContent ?? '').includes(text),
							val
						));
					await field.locator.click();
					for (const val of values[key]) {
						// Preset values (initialData) render as chips, not dropdown options — skip them
						if (await isPreset(val)) {
							continue;
						}
						const optionLocator = this.optionLocator(field, val);
						// If the option isn't immediately visible, type to trigger lazy search
						if (!(await optionLocator.isVisible())) {
							await field.locator.getByRole('combobox').fill(lazySearchText(val));
						}
						await expect(optionLocator).toBeVisible({ timeout: 10_000 });
						await optionLocator.click();
					}
					if (
						(await field.locator.isEnabled()) &&
						(await multiEl.count()) > 0 &&
						!(await multiEl.evaluate((el) => el.classList.contains('disabled')))
					) {
						await field.locator.press('Escape');
					}
					break;
				}
				case FormFieldType.DATE:
					await field.locator.clear();
				case FormFieldType.NUMBER:
					await field?.locator.fill(values[key].toString());
					break;
				case FormFieldType.DURATION:
					for (const unit of Object.keys(values[key])) {
						const locator = field?.locator.getByTestId(
							`form-input-${key.replaceAll('_', '-')}-${unit}`
						);
						await locator?.fill(values[key][unit].toString());
					}
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
