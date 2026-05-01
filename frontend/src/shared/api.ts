const BASE_URL = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseResponse(res: Response): Promise<unknown> {
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

function userMessage(code: string | undefined, fallback: string | undefined): string {
  switch (code) {
    case "AUTH_REQUIRED":
      return "Sessiya tugagan. Qayta kiring.";
    case "SESSION_FORBIDDEN":
    case "MENU_FORBIDDEN":
    case "ORDER_FORBIDDEN":
      return "Bu amal uchun ruxsat yo'q.";
    case "TABLE_NOT_FOUND":
      return "Stol topilmadi yoki faol emas.";
    case "INVALID_CREDENTIALS":
      return "Email yoki parol noto'g'ri.";
    case "ACCOUNT_DISABLED":
      return "Bu akkaunt o'chirilgan.";
    case "EMPTY_ORDER":
      return "Savat bo'sh.";
    case "ITEM_UNAVAILABLE":
      return "Tanlangan mahsulot hozir mavjud emas.";
    case "MISSING_IDEMPOTENCY_KEY":
    case "INVALID_IDEMPOTENCY_KEY":
      return "Buyurtmani yuborishda xatolik. Qayta urinib ko'ring.";
    case "RATE_LIMITED":
      return "Juda ko'p urinish bo'ldi. Bir daqiqadan keyin urinib ko'ring.";
    case "ORDER_NOT_FOUND":
      return "Buyurtma topilmadi.";
    case "INVALID_TRANSITION":
      return "Bu holatga o'tkazib bo'lmaydi.";
    case "CATEGORY_NOT_FOUND":
      return "Kategoriya topilmadi.";
    case "MENU_ITEM_NOT_FOUND":
      return "Mahsulot topilmadi.";
    case "TABLE_CODE_EXISTS":
      return "Bu stol kodi allaqachon mavjud.";
    case "VALIDATION_ERROR":
      return "Kiritilgan ma'lumotlarni tekshiring.";
    default:
      return fallback || "So'rov bajarilmadi.";
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  headers?: Record<string, string>,
): Promise<T> {
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: isForm ? headers : { "Content-Type": "application/json", ...headers },
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
    credentials: "include",
  });

  const data = await parseResponse(res);
  if (!res.ok) {
    const errorData = data as { error?: string; code?: string } | null;
    const code = errorData?.code || "HTTP_ERROR";
    throw new ApiError(
      res.status,
      code,
      userMessage(code, errorData?.error),
    );
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body: unknown, headers?: Record<string, string>) =>
    request<T>("POST", path, body, headers),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, formData: FormData) => request<T>("POST", path, formData),
};

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch("/health", { credentials: "include" });
  const data = await res.json();
  if (!res.ok) throw new ApiError(res.status, data.code || "HEALTH_ERROR", data.error || "Health failed");
  return data;
}
