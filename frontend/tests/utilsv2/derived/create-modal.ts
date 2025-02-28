import { CreateModal } from '../base/create-modal';
import { FolderCreateForm } from './model-form/folder-create-form';

export class FolderCreateModal extends CreateModal {
	getForm(): FolderCreateForm {
		return this._getSubElement(FolderCreateForm);
	}
}
