import { genericUrlmodelGET } from '$lib/utils/api-routes';

// This return an `{"message": "Internal Error"}` as the `/api/libraries` route doesn't exist in the backend.
// This endpoint is still defined to avoid route conflicts as it restablished the behavior expected from the `(app)/(internal)/[model=urlmodel]/+server.ts` file.
export const GET = genericUrlmodelGET('libraries');
