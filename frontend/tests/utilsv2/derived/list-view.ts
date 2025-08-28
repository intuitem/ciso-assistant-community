import { ListViewPage } from '../base/list-view-page';
import { FolderCreateModal } from './create-modal';
import type { Page as _Page, Expect, Locator } from '@playwright/test';
import type { Element } from '../core/element';
import { safeTranslate } from '$lib/utils/i18n';

export class FolderListViewPage extends ListViewPage {
	static CONTEXT: Element.Context = {
		URLModel: '/folders'
	};

	constructor(page: _Page) {
		super(page, '/folders');
	}

	async getOpenCreateModal(): Promise<FolderCreateModal> {
		return super._getOpenCreateModal(FolderCreateModal);
	}
}

export class QualificationListView extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/qualifications');
	}
}

export class LibraryListViewPage extends ListViewPage {
	protected _tabs: Locator;
	protected _libraryStoreTab: Locator;
	protected _loadedLibrariesTab: Locator;
	protected _customLibraryFileInput: Locator;
	protected _saveButton: Locator;

	constructor(page: _Page) {
		super(page, '/libraries');
		this._tabs = page.getByTestId('tabs-control');
		this._libraryStoreTab = this._tabs.first();
		this._loadedLibrariesTab = this._tabs.last();

		this._customLibraryFileInput = page.getByTestId('form-input-file');
		this._saveButton = page.getByTestId('save-button');
	}

	/** Clicks on the the "Library store" <Tab/> component. */
	async doClickLibraryStoreTab() {
		await this._libraryStoreTab.click();
	}

	/** Clicks on the the "Loaded libraries{...}" <Tab/> component. */
	async doClickLoadedLibrariesTab() {
		await this._loadedLibrariesTab.click();
	}

	/** Checks that the current number of loaded libraries is of `count` by reading the innerText of the "Loaded libraries{...}" <Tab/> component. */
	async checkLoadedLibraryCount(expect: Expect, count: number) {
		if (count < 1) {
			return await expect(this._tabs).toHaveCount(0);
		}
		await expect(this._tabs).toHaveCount(2);
		await expect(this._loadedLibrariesTab).toHaveText(
			`${safeTranslate('loadedLibraries')} ${count}`
		);
	}

	/** Returns the number of currently loaded libraries. */
	async getLoadedLibraryCount(): Promise<number> {
		const text = await this._loadedLibrariesTab.innerText();
		const libraryCount = Number(text.match(/[0-9]+$/));
		return libraryCount;
	}

	/** Uploads a custom library from the file located at `filePath`. */
	async doUploadCustomLibrary(expect: Expect, filePath: string) {
		const absoluteFilePath = new URL(filePath, import.meta.url).pathname;
		await this._customLibraryFileInput.setInputFiles(absoluteFilePath);
		await this._saveButton.click();
		const toast = this.getToast();
		await toast.checkIfVisible(expect);
		await toast.checkContainText(expect, safeTranslate('librarySuccessfullyLoaded'));
	}
}
