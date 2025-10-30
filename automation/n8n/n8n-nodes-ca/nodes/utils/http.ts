import type {
  IExecuteFunctions,
  IDataObject,
  IHttpRequestOptions,
} from "n8n-workflow";
import type { ICisoAssistantCredentials, IRequestConfig } from "../types";

/**
 * Build base HTTP request configuration with auth headers
 */
export function buildBaseConfig(
  credentials: ICisoAssistantCredentials,
): Partial<IHttpRequestOptions> {
  const config: Partial<IHttpRequestOptions> = {
    headers: {
      Authorization: `Token ${credentials.patKey}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    json: true,
  };

  // Skip TLS verification if specified in credentials
  if (credentials.skipTLS === true) {
    config.skipSslCertificateValidation = true;
  }

  return config;
}

/**
 * Make an HTTP request using n8n helpers
 */
export async function makeRequest(
  executeFunctions: IExecuteFunctions,
  credentials: ICisoAssistantCredentials,
  config: IRequestConfig,
): Promise<IDataObject> {
  const baseConfig = buildBaseConfig(credentials);

  const requestOptions: IHttpRequestOptions = {
    ...baseConfig,
    method: config.method,
    url: config.url,
    body: config.body,
    headers: {
      ...baseConfig.headers,
      ...config.headers,
    },
  };

  return await executeFunctions.helpers.httpRequest(requestOptions);
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
        ([_, value]) => value !== "" && value !== null && value !== undefined,
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
