export class DomainError extends Error {
  public readonly statusCode: number;
  public readonly details?: Record<string, unknown>;

  constructor(message: string, statusCode = 400, details?: Record<string, unknown>) {
    super(message);
    this.name = "DomainError";
    this.statusCode = statusCode;
    this.details = details;
  }
}
