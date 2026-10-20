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
    // The helper usually throws a NodeApiError already; re-wrapping returns it as is.
    const apiError = new NodeApiError(
      executeFunctions.getNode(),
      error as JsonObject,
    );
    if (itemIndex !== undefined) apiError.context.itemIndex = itemIndex;
    throw apiError;
  }
}

/**
 * Content-Disposition for an upload, mirroring the frontend's contentDispositionHeader:
 * ASCII-safe fallback (no CR/LF or quoting chars) plus an RFC 5987 filename*, which DRF's
 * FileUploadParser prefers and decodes. Keep filename* last: Django keeps the last `filename`.
 */
export function contentDispositionHeader(fileName: string): string {
  const asciiFileName = fileName
    .replace(/[^\x20-\x7E]/g, "-")
    .replace(/[;"%\\]/g, "-");
  return `attachment; filename="${asciiFileName}"; filename*=utf-8''${encodeURIComponent(fileName)}`;
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
