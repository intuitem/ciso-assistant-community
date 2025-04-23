import { Page } from '../core/page';
import type { Page as _Page } from '@playwright/test';
import { ADMIN_EMAIL, ADMIN_PASSWORD } from '../core/test-data';
import { AnalyticsPage } from './analytics-page';

/** Represents the `/login` page. */
export class LoginPage extends Page {
	constructor(page: _Page) {
		super(page, '/login');
	}

	/**
	 * Log in with the provided credentials (`email` and `password`).
	 * Note that this function will always return an `AnalyticsPage` object, no matter how the login operation goes.
	 */
	async doLoginP(email: string, password: string) {
		const usernameInput = this._self.getByTestId('form-input-username');
		const passwordInput = this._self.getByTestId('form-input-password');
		const loginButton = this._self.getByTestId('login-btn');
		await usernameInput.fill(email);
		await passwordInput.fill(password);
		await loginButton.click();
		return this._getGoto(AnalyticsPage);
	}

	/**
	 * Log in with the administrator credentials.
	 * Note that this function will always return an `AnalyticsPage` object, no matter how the login operation goes.
	 */
	async doLoginAdminP() {
		return this.doLoginP(ADMIN_EMAIL, ADMIN_PASSWORD);
	}
}
