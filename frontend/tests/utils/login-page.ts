import { expect, type Locator, type Page } from './test-utils.js';
import { BasePage } from './base-page.js';

enum State {
	Unset = -1,
	False = 0,
	True = 1
}

export class LoginPage extends BasePage {
	static readonly defaultEmail: string = 'admin@tests.com';
	static readonly defaultPassword: string = '1234';
	readonly usernameInput: Locator;
	readonly passwordInput: Locator;
	readonly loginButton: Locator;
	readonly emailInput: Locator;
	readonly sendEmailButton: Locator;
	readonly forgotPasswordButton: Locator;
	readonly newPasswordInput: Locator;
	readonly confirmPasswordInput: Locator;
	readonly setPasswordButton: Locator;
	email: string;
	password: string;

	constructor(public readonly page: Page) {
		super(page, '/login', 'Login');
		this.usernameInput = this.page.getByTestId('form-input-username');
		this.passwordInput = this.page.getByTestId('form-input-password');
		this.loginButton = this.page.getByTestId('login-btn');
		this.emailInput = this.page.getByTestId('form-input-email');
		this.sendEmailButton = this.page.getByTestId('send-btn');
		this.forgotPasswordButton = this.page.getByTestId('forgot-password-btn');
		this.newPasswordInput = this.page.getByTestId('form-input-new-password');
		this.confirmPasswordInput = this.page.getByTestId('form-input-confirm-new-password');
		this.setPasswordButton = this.page.getByTestId('set-password-btn');
		this.email = LoginPage.defaultEmail;
		this.password = LoginPage.defaultPassword;
	}

	async login(
		email: string = LoginPage.defaultEmail,
		password: string = LoginPage.defaultPassword
	) {
		this.email = email;
		this.password = password;
		await this.usernameInput.fill(email);
		await this.passwordInput.fill(password);
		await this.loginButton.click();
		if (email === LoginPage.defaultEmail && password === LoginPage.defaultPassword) {
			await this.page.waitForURL(/^.*\/((?!login).)*$/, { timeout: 10000 });
		} else {
			await this.page.waitForURL(/^.*\/login(\?next=\/.*)?$/);
		}
	}

	async hasUrl(redirect: State = State.Unset) {
		switch (redirect) {
			case State.Unset:
				// url can be /login or /login?next=/
				await expect(this.page).toHaveURL(/^.*\/login(\?next=\/.*)?$/);
				break;
			case State.False:
				// url must be /login
				await expect(this.page).toHaveURL(/^.*\/login$/);
				break;
			case State.True:
				//url must be /login?next=/
				await expect(this.page).toHaveURL(/^.*\/login\?next=\/.*$/);
				break;
		}
	}
}
