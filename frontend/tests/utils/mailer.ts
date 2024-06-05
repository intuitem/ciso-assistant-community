import { MailContent } from './mail-content.js';
import { expect, type Locator, type Page } from './test-utils.js';

class Email {
	readonly email: Locator;
	readonly from: Locator;
	readonly to: Locator;
	readonly subject: Locator;

	constructor(email: Locator) {
		this.email = email;
		this.from = email.locator('div:first-child').first();
		this.to = email.locator('div:first-child > div > div');
		this.subject = email.locator('.subject');
	}

	async hasWelcomeEmailDetails() {
		expect.soft(await this.getFrom()).toEqual('ciso-assistant@tests.net');
		expect.soft(await this.getSubject()).toEqual('Welcome to Ciso Assistant!');
	}

	async hasResetPasswordEmailDetails() {
		expect.soft(await this.getFrom()).toEqual('ciso-assistant@tests.net');
		expect.soft(await this.getSubject()).toEqual('CISO Assistant: Password Reset');
	}

	async hasEmailRecipient(recipient: string) {
		expect.soft(await this.getTo()).toEqual(recipient);
	}

	async getFrom() {
		return (await this.from.innerText()).split('\n')[0];
	}

	async getTo() {
		return await this.to.innerText();
	}

	async getSubject() {
		return await this.subject.innerText();
	}

	async open() {
		await this.email.click();
	}
}

export class Mailer {
	readonly url: string;
	readonly emailContent: MailContent;
	private readonly emails: Locator;

	constructor(public readonly page: Page) {
		this.url = 'http://localhost:' + (process.env.MAILER_WEB_SERVER_PORT || 8025);
		this.emailContent = new MailContent(page);
		this.emails = this.page.locator('.msglist-message');
	}

	async goto() {
		await this.page.goto(this.url);
		await this.page.waitForURL(this.url);
	}

	async hasUrl() {
		await expect(this.page).toHaveURL(this.url);
	}

	async getEmails() {
		const emailElements = await this.emails.all();
		const emails: Email[] = [];
		emailElements.forEach((email) => {
			emails.push(new Email(email));
		});

		return emails;
	}

	async getLastEmail() {
		return new Email(this.emails.first());
	}
}
