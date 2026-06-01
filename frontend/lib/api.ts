/** API base URL. In browser on same host use env; fallback localhost for dev. */
export function getApiUrl(): string {
  if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  return (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
}

export type NominalOption = {
  id: number;
  variant: string;
  nominal_rub: number;
  price_rub: number;
  available_count: number;
  can_buy: boolean;
};

export type Catalog = {
  spa_nominals: NominalOption[];
  ar_nominals: NominalOption[];
};

export async function fetchCatalog(): Promise<Catalog> {
  const res = await fetch(`${getApiUrl()}/api/catalog`, { cache: "no-store" });
  if (!res.ok) throw new Error("Не удалось загрузить номиналы");
  return res.json();
}

export type CreateOrderPayload = {
  denomination_id: number;
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string;
  consent_pd: boolean;
  consent_privacy: boolean;
};

export async function createOrder(payload: CreateOrderPayload) {
  const res = await fetch(`${getApiUrl()}/api/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Ошибка создания заказа");
  }
  return data as { order_id: string; public_token: string; redirect_url: string };
}

export type OrderStatus = {
  public_token: string;
  status: string;
  amount_rub: number;
  nominal_rub: number;
  variant: string;
  buyer_email: string;
  certificate_delivered: boolean;
  can_download_certificate: boolean;
};

export async function fetchOrderStatus(publicToken: string): Promise<OrderStatus> {
  const res = await fetch(`${getApiUrl()}/api/orders/${publicToken}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Заказ не найден");
  return res.json();
}

export function certificateDownloadUrl(publicToken: string): string {
  return `${getApiUrl()}/api/orders/${publicToken}/certificate.pdf`;
}
