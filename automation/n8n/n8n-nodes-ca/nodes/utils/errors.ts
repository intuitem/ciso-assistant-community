/**
 * Custom error class for CISO Assistant operations
 */
export class CisoAssistantError extends Error {
  constructor(
    message: string,
    public resource: string,
    public operation: string,
    public originalError?: unknown,
  ) {
    super(message);
    this.name = "CisoAssistantError";
  }
}

/**
 * Format error for n8n output
 */
export function formatError(
  error: unknown,
  resource: string,
  operation: string,
): string {
  if (error instanceof Error) {
    return `[${resource}/${operation}] ${error.message}`;
  }
  return `[${resource}/${operation}] ${String(error)}`;
}

/**
 * Handle operation errors
 */
export function handleOperationError(
  error: unknown,
  resource: string,
  operation: string,
): never {
  const message = formatError(error, resource, operation);
  throw new CisoAssistantError(message, resource, operation, error);
}
