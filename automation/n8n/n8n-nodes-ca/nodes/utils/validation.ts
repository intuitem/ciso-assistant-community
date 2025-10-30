import type { IDataObject } from "n8n-workflow";

/**
 * Sentinel values that should be treated as "not set" in update operations
 */
const UPDATE_SENTINEL_VALUES = {
  string: ["", "--"],
  number: [-1],
  boolean: [], // No boolean sentinels by default
};

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
 * Build request body for update operations, filtering out sentinel values
 * Sentinel values (like "", "--", -1) are treated as "field not set" and excluded
 * This prevents unintended field resets when updating resources
 */
export function buildUpdateBody(fields: IDataObject = {}): IDataObject {
  const body: IDataObject = {};

  Object.entries(fields).forEach(([key, value]) => {
    // Skip null and undefined
    if (value === null || value === undefined) {
      return;
    }

    // Check for sentinel values based on type
    if (typeof value === "string") {
      // Skip empty strings and placeholder values
      if (!UPDATE_SENTINEL_VALUES.string.includes(value)) {
        body[key] = value;
      }
    } else if (typeof value === "number") {
      // Skip sentinel numeric values like -1
      if (!UPDATE_SENTINEL_VALUES.number.includes(value)) {
        body[key] = value;
      }
    } else {
      // Include all other types (booleans, arrays, objects, etc.)
      body[key] = value;
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
