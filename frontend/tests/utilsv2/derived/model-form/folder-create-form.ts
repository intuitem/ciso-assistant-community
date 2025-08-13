import { ModelForm } from '../../base/model-form';
import type { Locator } from '@playwright/test';
import type { Element } from '../../core/element';

// The AutoCompleteSelect should be later handled by a class instead of a single function like this.
async function selectChoice(input: Locator, value: string) {
	const inputSearch = input.locator('ul.selected input');
	const firstOption = input.locator(`[role="option"]`, { hasText: value }).first();

	const searchBox = input.getByRole('searchbox');
	const searchBoxClasses = await searchBox.getAttribute('class');

	const searchBoxClasses2 = await searchBox.getAttribute('class');
	if (searchBoxClasses && searchBoxClasses.indexOf('disabled') >= 0) return;

	await inputSearch.fill(value);
	await firstOption.focus();
	// Clicking only once doesn't seem to work for whatever reason
	await firstOption.click({ force: true });
}

interface FolderData {
	name: string;
	description?: string;
	parentDomain?: string;
}

export class FolderCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _parentDomainInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name'); // document.querySelector(`[data-testid="form-input-name"]`);
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._parentDomainInput = this._self.getByTestId('form-input-parent-folder');
	}

	async doFillForm(data: FolderData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		if (data.parentDomain) {
			await this._waitLoadingSpins();
			await selectChoice(this._parentDomainInput, data.parentDomain);
		}
	}
}
