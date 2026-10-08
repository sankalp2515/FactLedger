export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
  ) {
    super(message);
  }
}
export class ApiClient {
  csrf = "";
  async get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }
  async command<T>(path: string, body: unknown, method = "POST"): Promise<T> {
    return this.request<T>(path, {
      method,
      body: body instanceof FormData ? body : JSON.stringify(body),
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
  }
  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (init.body && !(init.body instanceof FormData))
      headers.set("Content-Type", "application/json");
    if (init.method && init.method !== "GET")
      headers.set("X-CSRF-Token", this.csrf);
    let response: Response;
    try {
      response = await fetch(`/v1${path}`, {
        ...init,
        headers,
        credentials: "same-origin",
      });
    } catch {
      throw new ApiError(
        0,
        "NETWORK_ERROR",
        "Cannot reach the research service. Check your connection and try again.",
      );
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = data.detail ?? data;
      throw new ApiError(
        response.status,
        typeof detail === "object"
          ? (detail.code ?? "REQUEST_FAILED")
          : "REQUEST_FAILED",
        typeof detail === "string"
          ? detail
          : (detail.message ?? "The request could not be completed."),
        detail.request_id,
      );
    }
    return data as T;
  }
}
export const api = new ApiClient();
