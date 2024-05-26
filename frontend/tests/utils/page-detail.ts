import { getObjectNameWithoutScope, expect, type Locator, type Page } from './test-utils.js';
import { FormContent, FormFieldType } from './form-content.js';
import { BasePage } from './base-page.js';

export class PageDetail extends BasePage {
	readonly form: FormContent;
	item: string;
	readonly editButton: Locator;

	constructor(public readonly page: Page, url: string, form: FormContent, item: string) {
		super(page, url, item);
		this.form = form;
		this.item = item;
		this.editButton = this.page.getByTestId('edit-button');
	}

	setItem(item: string) {
		this.item = item;
	}

	async editItem(buildParams: { [k: string]: string }, editParams: { [k: string]: string }) {
		await this.editButton.click();
		await this.hasTitle('Edit ' + this.item);
		await this.hasBreadcrumbPath(['Edit'], false);

		let editedValues: { [k: string]: string } = {};
		for (const key in editParams) {
			editedValues[key] = editParams[key] === '' ? buildParams[key] + ' edited' : editParams[key];
		}

		await this.form.fill(editedValues);
		await this.form.saveButton.click();

		await this.isToastVisible(
			'The .+: ' +
				({ ...buildParams, ...editedValues }.name || { ...buildParams, ...editedValues }.email) +
				' has been successfully updated'
		);
		return editedValues;
	}

	async verifyItem(values: { [k: string]: any }) {
		if (this.url.includes('risk-assessments')) {
			if ('project' in values) {
				await expect
					.soft(this.page.getByTestId('name-field-value'))
					.toHaveText(`${values.project}/${values.name} - ${values.version}`);
			} else {
				await expect
					.soft(this.page.getByTestId('name-field-value'))
					.toHaveText(new RegExp(`.+/${values.name} - ${values.version}`));
			}
			if ('risk_matrix' in values) {
				await expect
					.soft(this.page.getByTestId('risk-matrix-field-title'))
					.toHaveText('Risk matrix:');
				await expect
					.soft(this.page.getByTestId('risk-matrix-field-value'))
					.toHaveText(values.risk_matrix);
			}

			await expect
				.soft(this.page.getByTestId('description-field-title'))
				.toHaveText('Description:');
			await expect
				.soft(this.page.getByTestId('description-field-value'))
				.toHaveText(values.description);
		} else {
			for (const key in values) {
				if (await this.page.getByTestId(key.replaceAll('_', '-') + '-field-title').isVisible()) {
					if (key === 'lc_status') {
						//TODO replace this with a better solution
						await expect
							.soft(this.page.getByTestId(key.replaceAll('_', '-') + '-field-title'))
							.toHaveText(new RegExp(key.replaceAll('_', ' ').replace('lc ', ''), 'i'));
					} else {
						await expect
							.soft(this.page.getByTestId(key.replaceAll('_', '-') + '-field-title'))
							.toHaveText(new RegExp(key.replaceAll('_', ' '), 'i'));
					}

					if (this.form.fields.get(key)?.type === FormFieldType.CHECKBOX) {
						await expect
							.soft(this.page.getByTestId(key.replaceAll('_', '-') + '-field-value'))
							.toHaveText(values[key] ? 'true' : '--');
					} else if (this.form.fields.get(key)?.type === FormFieldType.DATE) {
						const displayedValue = await this.page
							.getByTestId(key.replaceAll('_', '-') + '-field-value')
							.innerText();

						const displayedDate = new Date(displayedValue);
						const date = new Date(values[key]);

						expect
							.soft(displayedValue)
							.toMatch(
								/(\d{1,2}\/\d{1,2}\/\d{4})|(\d{1,2}\/\d{1,2}\/\d{2})|(\d{4}-\d{2}-\d{2}),\s\d{1,2}(:\d{1,2}){2} (AM|PM)/
							);
						expect.soft(displayedDate.getFullYear()).toBe(date.getFullYear());
						expect.soft(displayedDate.getMonth()).toBe(date.getMonth());
						expect.soft(displayedDate.getDate()).toBe(date.getDate());
					} else if (this.form.fields.get(key)?.type === FormFieldType.FILE) {
						const displayedValue = await this.page
							.getByTestId(key.replaceAll('_', '-') + '-field-value')
							.innerText();
						const fileName = values[key]?.split('/')?.pop()?.split('.') ?? [];

						expect
							.soft(displayedValue)
							.toMatch(new RegExp(fileName[0] + '(_.{7})?' + '.' + fileName[1]));
					} else {
						const value = this.page.getByTestId(key.replaceAll('_', '-') + '-field-value');
						if ((await value.allInnerTexts()).length > 1) {
							await expect
								.soft(await value.allInnerTexts())
								.toHaveTextUnordered(
									typeof values[key] === 'object' && !Array.isArray(values[key])
										? values[key].value
										: values[key]
								);
						} else {
							await expect
								.soft(value)
								.toContainText(
									getObjectNameWithoutScope(
										typeof values[key] === 'object'
											? !Array.isArray(values[key])
												? values[key].value
												: values[key][0]
											: values[key]
									),
									{ ignoreCase: true }
								);
						}
					}
				}
			}
		}
	}

	async treeViewItem(value: string, path: string[] = []) {
		if (path.length !== 0) {
			const tree = [...path, value];
			for (let i = 0; i < tree.length - 1; i++) {
				if (
					await this.page
						.getByTestId('tree-item-content')
						.getByText(tree[i + 1])
						.isHidden()
				) {
					await this.page.getByTestId('tree-item-content').getByText(tree[i]).click();
				}
			}
		}
		const content = this.page
			.getByTestId('tree-item-content')
			.filter({ hasText: new RegExp(`^${value}\n*.*`) });
		return {
			content: content,
			progressRadial: this.page
				.getByTestId('tree-item')
				.filter({ has: content, hasNotText: path.length != 0 ? path.at(-1) : undefined })
				.getByTestId('tree-item-lead')
				.getByTestId('progress-radial'),
			default: this.page.getByTestId('tree-item').filter({ hasText: new RegExp(`^${value}\n*.*`) })
		};
	}
}
