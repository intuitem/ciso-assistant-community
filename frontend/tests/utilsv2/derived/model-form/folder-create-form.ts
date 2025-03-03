import { ModelForm } from '../../base/model-form';
import type { Locator } from '@playwright/test';
import type { Element } from '../../core/element';

interface FolderData {
	name: string;
	description: string;
}

export class FolderCreateForm extends ModelForm {
	private _name_input: Locator;
	private _description_input: Locator;

	// Replace all the internal this.getSelf() calls by this._self in the codebase !
	// Replace all the internal this.getSelf() calls by this._self in the codebase !
	// Replace all the internal this.getSelf() calls by this._self in the codebase !

	constructor(...args: Element.Args) {
		super(...args);
		this._name_input = this._self.getByTestId('form-input-name');
		this._description_input = this._self.getByTestId('form-input-description');
	}

	async doFillForm(data: FolderData) {
		await this._name_input.fill(data.name ?? '');
		await this._description_input.fill(data.description ?? '');
	}
}
