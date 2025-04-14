import type { Page as _Page, Locator } from '@playwright/test';
import { Element } from '../core/element';
import type { Expect } from '@playwright/test';

/** Represents the `<Sidebar/>` component. */
export class Sidebar extends Element {
	private _sections: Locator;
	private _toggleButton: Locator;
	static DATA_TESTID = 'sidebar';

	constructor(...args: Element.Args) {
		super(...args);
		// To fix: These Test IDs must end with "-elem" based on the spec.
		this._sections = this._self.getByTestId('accordion-item');
		this._toggleButton = this._self.getByTestId('sidebar-toggle-btn');
	}

	/**
	 * Clicks on the toggle button, which either opens or closes the sidebar depending on its current visibility.
	 */
	async doToggle() {
		await this._toggleButton.click();
	}

	/** Check if the sidebar is opened. */
	async checkIsOpened(expect: Expect) {
		return expect(this._toggleButton).toHaveClass(/rotate-180/);
	}

	/** Check if the sidebar is closed. */
	async checkIsClosed(expect: Expect) {
		return expect(this._toggleButton).not.toHaveClass(/rotate-180/);
	}

	// Missing docstring
	async getGotoDomain() {
		const accordionItemToOpen: Locator = await this._sections.filter({
			hasText: 'Organization' // This is case-insensitive
		});
		await accordionItemToOpen.click();
		const domainLink = accordionItemToOpen.getByTestId('accordion-item-folders');
		await domainLink.click();
	}

	/** Log out the user from the current session (by clicking the logout button). */
	async doLogout() {
		const moreButton = this._self.getByTestId('sidebar-more-btn');
		await moreButton.click();
		const logoutButton = this._self.getByTestId('logout-button');
		await logoutButton.isVisible();
		await logoutButton.click();
	}
}
