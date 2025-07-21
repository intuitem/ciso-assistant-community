import { ModelForm } from '../base/model-form';
import type { Locator } from '@playwright/test';
import type { Element } from '../core/element';

// The AutoCompleteSelect should be later handled by a class instead of a single function like this.
async function selectChoice(input: Locator, value: string) {
	const inputSearch = input.locator('ul.selected input');
	const firstOption = input.locator(`[role="option"]`).first();

	await inputSearch.fill(value);
	// Clicking only once doesn't seem to work for whatever reason
	await firstOption.click({ force: true });
	await firstOption.click({ force: true });
}

interface FolderData {
	name: string;
	description?: string;
}

export class FolderCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
	}

	async doFillForm(data: FolderData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');
	}
}

interface PerimeterData {
	name: string;
	description?: string;
}

export class PerimeterCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
	}

	/** This function doesn't support the `folder` argument. */
	async doFillForm(data: PerimeterData) {
		await this._waitLoadingSpins();
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');
	}
}

interface AssetData {
	name: string;
	description?: string;
	folder: string;
}

export class AssetCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _domainInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._self.getByTestId('form-input-folder');
	}

	async doFillForm(data: AssetData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await selectChoice(this._domainInput, data.folder);
	}
}

interface AppliedControlData {
	name: string;
	description?: string;
	folder: string;
}

export class AppliedControlCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _domainInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._self.getByTestId('form-input-folder');
	}

	async doFillForm(data: AppliedControlData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await selectChoice(this._domainInput, data.folder);
	}
}

interface ExceptionData {
	name: string;
	description?: string;
	folder: string;
}

export class ExceptionCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _domainInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._self.getByTestId('form-input-folder');
	}

	async doFillForm(data: ExceptionData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await selectChoice(this._domainInput, data.folder);
	}
}

interface ComplianceAssessmentData {
	name: string;
	description?: string;
}

export class ComplianceAssessmentCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
	}

	async doFillForm(data: ComplianceAssessmentData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
	}
}

interface RiskAcceptanceData {
	name: string;
	description?: string;
	riskScenarios: string;
}

export class RiskAcceptanceCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _riskScenariosInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._riskScenariosInput = this._self.getByTestId('form-input-risk-scenarios');
	}

	async doFillForm(data: RiskAcceptanceData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await selectChoice(this._riskScenariosInput, data.riskScenarios);
	}
}

interface RiskScenarioData {
	name: string;
	description?: string;
}

export class RiskScenarioCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
	}

	async doFillForm(data: RiskScenarioData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
	}
}

interface RiskAssessmentData {
	name: string;
	description?: string;
}

export class RiskAssessmentCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
	}

	async doFillForm(data: RiskAssessmentData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
	}
}

interface EvidenceData {
	name: string;
	description?: string;
	folder: string;
}

export class EvidenceCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _domainInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._self.getByTestId('form-input-folder');
	}

	async doFillForm(data: EvidenceData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await selectChoice(this._domainInput, data.folder);
	}
}

interface ThreatData {
	name: string;
	description?: string;
	folder: string;
}

export class ThreatCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _domainInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._self.getByTestId('form-input-folder');
	}

	async doFillForm(data: ThreatData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await selectChoice(this._domainInput, data.folder);
	}
}

interface UserData {
	email: string;
}

export class UserCreateForm extends ModelForm {
	private _emailInput: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._emailInput = this._self.getByTestId('form-input-email');
	}

	async doFillForm(data: UserData) {
		await this._emailInput.fill(data.email);
	}
}
