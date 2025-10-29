import type { IDataObject } from "n8n-workflow";

/**
 * Build request body with conditional fields
 * Only includes fields that have values (not empty strings, null, or undefined)
 */
export function buildRequestBody(
  requiredFields: IDataObject,
  optionalFields: IDataObject = {},
): IDataObject {
  const body = { ...requiredFields };

  // Add optional fields only if they have values
  Object.entries(optionalFields).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      // Special handling for numbers: include -1 and 0 as valid values
      if (typeof value === "number" && value >= -1) {
        body[key] = value;
      } else if (typeof value !== "number") {
        body[key] = value;
      }
    }
  });

  return body;
}

/**
 * Validate required parameters
 */
export function validateRequired(
  params: IDataObject,
  requiredFields: string[],
): void {
  const missing = requiredFields.filter(
    (field) =>
      params[field] === undefined ||
      params[field] === null ||
      params[field] === "",
  );

  if (missing.length > 0) {
    throw new Error(`Missing required fields: ${missing.join(", ")}`);
  }
}

/**
 * Convert snake_case to camelCase
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Convert camelCase to snake_case
 */
export function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

/**
 * Convert object keys from camelCase to snake_case
 */
export function keysToSnakeCase(obj: IDataObject): IDataObject {
  const result: IDataObject = {};

  Object.entries(obj).forEach(([key, value]) => {
    result[camelToSnake(key)] = value;
  });

  return result;
}
