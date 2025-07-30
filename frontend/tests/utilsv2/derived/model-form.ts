import { ModelForm } from '../base/model-form';
import type { Locator, Expect } from '@playwright/test';
import type { Element } from '../core/element';
import { AutoCompleteSelectInput } from '../base/autocomplete-select-input';

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

	async doFillForm(expect: Expect, data: FolderData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');
	}
}

interface PerimeterData {
	name: string;
	description?: string;
	folder?: string;
}

export class PerimeterCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _domainInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-folder'
		});
	}

	async doFillForm(expect: Expect, data: PerimeterData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');
		await this._waitLoadingSpins();
		if (data.folder) await this._domainInput.select(expect, data.folder);
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
	private _domainInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-folder'
		});
	}

	async doFillForm(expect: Expect, data: AssetData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await this._domainInput.select(expect, data.folder);
	}
}

interface AppliedControlData {
	name: string;
	description?: string;
	folder?: string;
}

export class AppliedControlCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _domainInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-folder'
		});
	}

	async doFillForm(expect: Expect, data: AppliedControlData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		if (data.folder) await this._domainInput.select(expect, data.folder);
	}
}

export const AppliedControlDuplicateForm = AppliedControlCreateForm;

interface ExceptionData {
	name: string;
	description?: string;
	folder: string;
}

export class ExceptionCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _domainInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-folder'
		});
	}

	async doFillForm(expect: Expect, data: ExceptionData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await this._domainInput.select(expect, data.folder);
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

	async doFillForm(expect: Expect, data: ComplianceAssessmentData) {
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
	private _riskScenariosInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._riskScenariosInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-risk-scenarios'
		});
	}

	async doFillForm(expect: Expect, data: RiskAcceptanceData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await this._riskScenariosInput.select(expect, data.riskScenarios);
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

	async doFillForm(expect: Expect, data: RiskScenarioData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
	}
}

interface RiskAssessmentData {
	name: string;
	description?: string;
	perimeter: string;
	risk_matrix: string;
}

export class RiskAssessmentCreateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _perimeterInput: AutoCompleteSelectInput;
	private _riskMatrixInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._perimeterInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-perimeter'
		});
		this._riskMatrixInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-risk-matrix'
		});
	}

	async doFillForm(expect: Expect, data: RiskAssessmentData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await this._perimeterInput.select(expect, data.perimeter);
		if (data.risk_matrix) await this._riskMatrixInput.select(expect, data.risk_matrix);
	}
}

interface RiskAssessmentDuplicateData {
	name: string;
	description?: string;
	perimeter: string;
}

export class RiskAssessmentDuplicateForm extends ModelForm {
	private _nameInput: Locator;
	private _descriptionInput: Locator;
	private _perimeterInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._perimeterInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-perimeter'
		});
	}

	async doFillForm(expect: Expect, data: RiskAssessmentDuplicateData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await this._perimeterInput.select(expect, data.perimeter);
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
	private _domainInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-folder'
		});
	}

	async doFillForm(expect: Expect, data: EvidenceData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await this._domainInput.select(expect, data.folder);
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
	private _domainInput: AutoCompleteSelectInput;

	constructor(...args: Element.Args) {
		super(...args);
		this._nameInput = this._self.getByTestId('form-input-name');
		this._descriptionInput = this._self.getByTestId('form-input-description');
		this._domainInput = this._getSubElement(AutoCompleteSelectInput, {
			dataTestId: 'form-input-folder'
		});
	}

	async doFillForm(expect: Expect, data: ThreatData) {
		await this._nameInput.fill(data.name);
		await this._descriptionInput.fill(data.description ?? '');

		await this._waitLoadingSpins();
		await this._domainInput.select(expect, data.folder);
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

	async doFillForm(expect: Expect, data: UserData) {
		await this._emailInput.fill(data.email);
	}
}
