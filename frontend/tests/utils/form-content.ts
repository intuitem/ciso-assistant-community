import { expect, type Locator, type Page } from './test-utils.js';

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const stripLeadingSlash = (value: string) => value.replace(/^\/+/, '');

const buildSearchboxMatcher = (value: string): RegExp => {
	const raw = String(value).trim();
	const normalized = stripLeadingSlash(raw);
	const escaped = escapeRegExp(normalized);
	if (!raw.includes('/')) {
		return new RegExp(`\\s*/?${escaped}\\s*`);
	}
	const suffix = stripLeadingSlash(raw.split('/').pop()?.trim() ?? '');
	if (!suffix || suffix === raw) {
		return new RegExp(`\\s*/?${escaped}\\s*`);
	}
	return new RegExp(`\\s*(?:/?${escaped}|/?${escapeRegExp(suffix)})\\s*`);
};

const buildOptionMatcher = (value: string): string | RegExp => {
	const raw = String(value).trim();
	const normalized = stripLeadingSlash(raw);
	const escaped = escapeRegExp(normalized);
	if (!raw.includes('/')) {
		return new RegExp(`^\\s*(?:/?${escaped}|.*${escapeRegExp(raw)})\\s*$`);
	}
	const suffix = stripLeadingSlash(raw.split('/').pop()?.trim() ?? '');
	if (!suffix || suffix === raw) {
		return new RegExp(`^\\s*/?${escaped}\\s*$`);
	}
	// Match either the full path or just the final suffix (which may have UUID prefixes)
	return new RegExp(`^\\s*(?:.*${escapeRegExp(suffix)})\\s*$`);
};

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
			for (const spinner of await this.page.locator('.loading-spinner').all()) {
				await expect(spinner).not.toBeVisible({
					timeout: 20_000
				});
			}

			// Check if this is a markdown field (description, observation, or justification) and handle it
			if (
				(key === 'description' || key === 'observation' || key === 'justification') &&
				field?.type === FormFieldType.TEXT
			) {
				// Try to click the markdown edit button if it exists
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
						if (
							(await field.locator.getByRole('option').isVisible()) &&
							(await field.locator
								.getByRole('searchbox')
								.evaluate((el) => el.classList.contains('disabled')))
						) {
							const matcher = buildSearchboxMatcher(values[key]);
							await expect(field.locator.getByRole('searchbox')).toContainText(matcher);
						} else {
							if (typeof values[key] === 'object' && 'request' in values[key]) {
								const responsePromise = this.page.waitForResponse(
									(resp) => resp.url().includes(values[key].request.url) && resp.status() === 200
								);
								await field.locator.click();
								await expect(
									field.locator
										.getByRole('option', { name: buildOptionMatcher(values[key].value) })
										.first()
								).toBeVisible({ timeout: 10_000 });
								await field.locator
									.getByRole('option', { name: buildOptionMatcher(values[key].value) })
									.first()
									.click();

								await responsePromise;
							} else {
								await field.locator.click();
								await expect(
									field.locator
										.getByRole('option', { name: buildOptionMatcher(values[key]) })
										.first()
								).toBeVisible({ timeout: 10_000 });
								await field.locator
									.getByRole('option', { name: buildOptionMatcher(values[key]) })
									.first()
									.click();
							}
						}
					}).toPass({ timeout: 22_000, intervals: [500, 1000, 10_000] });
					break;
				case FormFieldType.SELECT_MULTIPLE_AUTOCOMPLETE:
					await field.locator.click();
					for (const val of values[key]) {
						const matcher = buildOptionMatcher(val);
						await expect(
							field.locator.getByRole('option', { name: matcher }).first()
						).toBeVisible();
						await field.locator.getByRole('option', { name: matcher }).first().click();
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
