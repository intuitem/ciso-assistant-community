import { CreateModal } from '../base/create-modal';
import {
	FolderCreateForm,
	PerimeterCreateForm,
	AssetCreateForm,
	AppliedControlCreateForm,
	AppliedControlDuplicateForm,
	ExceptionCreateForm,
	ComplianceAssessmentCreateForm,
	EvidenceCreateForm,
	RiskAssessmentCreateForm,
	RiskAssessmentDuplicateForm,
	ThreatCreateForm,
	RiskScenarioCreateForm,
	RiskAcceptanceCreateForm,
	UserCreateForm
} from './model-form';

export class FolderCreateModal extends CreateModal {
	getForm(): FolderCreateForm {
		return this._getSubElement(FolderCreateForm);
	}
}

export class PerimeterCreateModal extends CreateModal {
	getForm(): PerimeterCreateForm {
		return this._getSubElement(PerimeterCreateForm);
	}
}

export class AssetCreateModal extends CreateModal {
	getForm(): AssetCreateForm {
		return this._getSubElement(AssetCreateForm);
	}
}

export class AppliedControlCreateModal extends CreateModal {
	getForm(): AppliedControlCreateForm {
		return this._getSubElement(AppliedControlCreateForm);
	}
}

export class AppliedControlDuplicateModal extends CreateModal {
	getForm(): AppliedControlDuplicateForm {
		return this._getSubElement(AppliedControlDuplicateForm);
	}
}

export class ExceptionCreateModal extends CreateModal {
	getForm(): ExceptionCreateForm {
		return this._getSubElement(ExceptionCreateForm);
	}
}

export class ComplianceAssessmentCreateModal extends CreateModal {
	getForm(): ComplianceAssessmentCreateForm {
		return this._getSubElement(ComplianceAssessmentCreateForm);
	}
}

export class EvidenceCreateModal extends CreateModal {
	getForm(): EvidenceCreateForm {
		return this._getSubElement(EvidenceCreateForm);
	}
}

export class RiskAssessmentCreateModal extends CreateModal {
	getForm(): RiskAssessmentCreateForm {
		return this._getSubElement(RiskAssessmentCreateForm);
	}
}

export class RiskAssessmentDuplicateModal extends CreateModal {
	getForm(): RiskAssessmentDuplicateForm {
		return this._getSubElement(RiskAssessmentDuplicateForm);
	}
}

export class ThreatCreateModal extends CreateModal {
	getForm(): ThreatCreateForm {
		return this._getSubElement(ThreatCreateForm);
	}
}

export class RiskScenarioCreateModal extends CreateModal {
	getForm(): RiskScenarioCreateForm {
		return this._getSubElement(RiskScenarioCreateForm);
	}
}

export class RiskAcceptanceCreateModal extends CreateModal {
	getForm(): RiskAcceptanceCreateForm {
		return this._getSubElement(RiskAcceptanceCreateForm);
	}
}

export class UserCreateModal extends CreateModal {
	getForm(): UserCreateForm {
		return this._getSubElement(UserCreateForm);
	}
}
