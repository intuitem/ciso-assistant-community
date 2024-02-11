import { expect, type Page } from './test-utils';
import { BasePage } from './base-page';

enum State {
	Unset = -1,
	False = 0,
	True = 1
}

export class LoginPage extends BasePage {
	readonly email: string = 'admin@tests.com';
	readonly password: string = '1234';

	constructor(public readonly page: Page) {
		super(page, '/login', 'Login');
	}

	async login(email: string = this.email, password: string = this.password) {
		await this.page.locator('input[name="username"]').fill(email);
		await this.page.locator('input[name="password"]').fill(password);
		await this.page.getByRole('button', { name: 'Log in' }).click();
		if (email === this.email && password === this.password) {
			// await this.page.waitForURL('/[!login]*', { timeout: 10000 });
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
