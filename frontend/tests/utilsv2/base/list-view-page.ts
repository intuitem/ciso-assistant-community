import { Page } from '../core/page';
import { notImplemented } from '../core/base';
import { CreateModal } from './create-modal';
import type { Page as _Page, Locator } from '@playwright/test';
import type { Element } from '../core/element';
import { Toast } from '../derived/toast';
import { ModelTable } from './model-table';

export class ListViewPage extends Page {
	constructor(page: _Page, endpoint: string) {
		super(page, endpoint);
	}

	async getOpenCreateModal(): Promise<CreateModal> {
		notImplemented();
	}

	getToast() {
		return this._getSubElement(Toast);
	}

	getModelTable() {
		return this._getSubElement(ModelTable);
	}

	protected async _getOpenCreateModal<T = CreateModal>(
		createModalClass: Element.Class<T>
	): Promise<T> {
		// Should it be renamed "add-button-elem" instead ?
		const locator = this._self.getByTestId('add-button');
		await locator.click();

		return this._getSubElement(createModalClass);
	}
}
export namespace ListViewPage {
	export type Derived = new (page: _Page) => ListViewPage;
}
