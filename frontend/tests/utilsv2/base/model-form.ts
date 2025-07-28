import { Element } from '../core/element';
import { notImplemented } from '../core/base';
import type { Locator } from '@playwright/test';

export class ModelForm extends Element {
	static DATA_TESTID = 'model-form';
	protected _saveButton: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._saveButton = this._self.getByTestId('save-button');
	}

	async doFillForm(formData: { [key: string]: any }) {
		notImplemented();
	}

	async doSubmit() {
		await this._saveButton.click({ force: true });
		const isStillVisible = await this._saveButton.isVisible();
		if (isStillVisible) {
			await this._saveButton.click();
		}
	}

	async _waitLoadingSpins() {
		const loadingSpins = await this._self.getByTestId('autocomplete-select-loading-spinner-elem').all();
		for (const loadingSpin of loadingSpins) {
			await loadingSpin.waitFor({ state: 'detached' });
		}
	}
}
