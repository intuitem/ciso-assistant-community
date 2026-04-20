import { genericUrlmodelIdFieldGET, genericUrlmodelIdFieldPATCH } from '$lib/utils/api-routes';

export const GET = genericUrlmodelIdFieldGET('asset-assessments', 'dependencies');
export const PATCH = genericUrlmodelIdFieldPATCH('asset-assessments', 'dependencies');
