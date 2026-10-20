import { NodeApiError } from "n8n-workflow";
import type {
  IExecuteFunctions,
  IDataObject,
  IHttpRequestOptions,
  JsonObject,
} from "n8n-workflow";
import type { ICisoAssistantCredentials, IRequestConfig } from "../types";

/**
 * Make an authenticated HTTP request using n8n helpers
 */
export async function makeRequest(
  executeFunctions: IExecuteFunctions,
  credentials: ICisoAssistantCredentials,
  config: IRequestConfig,
  itemIndex?: number,
): Promise<IDataObject> {
  const requestOptions: IHttpRequestOptions = {
    method: config.method,
    url: config.url,
    body: config.body,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...config.headers,
    },
    json: true,
    skipSslCertificateValidation: credentials.skipTLS === true,
  };

  try {
    return await executeFunctions.helpers.httpRequestWithAuthentication.call(
      executeFunctions,
      "cisoAssistantApi",
      requestOptions,
    );
  } catch (error) {
    throw new NodeApiError(executeFunctions.getNode(), error as JsonObject, {
      itemIndex,
    });
  }
}

/**
 * Build URL with query parameters
 */
export function buildUrl(
  baseUrl: string,
  path: string,
  params?: Record<string, string | number | boolean>,
): string {
  let url = `${baseUrl}${path}`;

  if (params && Object.keys(params).length > 0) {
    const queryParams = Object.entries(params)
      .filter(
        ([, value]) => value !== "" && value !== null && value !== undefined,
      )
      .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
      .join("&");

    if (queryParams) {
      url += `?${queryParams}`;
    }
  }

  return url;
}

/**
 * Build filter parameters for list operations
 */
export function buildFilterParams(
  folderIdFilter?: string,
  perimeterIdFilter?: string,
  additionalFilters?: Record<string, string>,
): Record<string, string> {
  const params: Record<string, string> = {};

  if (folderIdFilter) {
    params.folder = folderIdFilter;
  }

  if (perimeterIdFilter) {
    params.perimeter = perimeterIdFilter;
  }

  if (additionalFilters) {
    Object.assign(params, additionalFilters);
  }

  return params;
}
