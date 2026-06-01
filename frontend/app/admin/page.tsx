"use client";

import { useCallback, useEffect, useState } from "react";

import { getApiUrl } from "@/lib/api";

const API_URL = getApiUrl();

type StockRow = {
  denomination_id: number;
  variant: string;
  nominal_rub: number;
  available: number;
  reserved: number;
  sold: number;
};

type PendingOrder = {
  id: string;
  public_token: string;
  buyer_email: string;
  nominal_rub: number;
  created_at: string | null;
};

function authHeader(): string {
  const user = prompt("Логин админки");
  const pass = prompt("Пароль админки");
  if (!user || !pass) return "";
  return "Basic " + btoa(`${user}:${pass}`);
}

export default function AdminPage() {
  const [stock, setStock] = useState<StockRow[]>([]);
  const [pending, setPending] = useState<PendingOrder[]>([]);
  const [auth, setAuth] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const loadStock = useCallback(async (header: string) => {
    const res = await fetch(`${API_URL}/admin/stock`, {
      headers: { Authorization: header },
    });
    if (!res.ok) throw new Error("Ошибка загрузки остатков");
    setStock(await res.json());
  }, []);

  const loadPending = useCallback(async (header: string) => {
    const res = await fetch(`${API_URL}/admin/orders/pending-delivery`, {
      headers: { Authorization: header },
    });
    if (res.ok) setPending(await res.json());
  }, []);

  useEffect(() => {
    const h = authHeader();
    if (!h) return;
    setAuth(h);
    loadStock(h).catch((e) => setMessage(e.message));
    loadPending(h).catch(() => undefined);
  }, [loadStock, loadPending]);

  const retryDelivery = async (orderId: string) => {
    if (!auth) return;
    const res = await fetch(`${API_URL}/admin/orders/${orderId}/retry-delivery`, {
      method: "POST",
      headers: { Authorization: auth },
    });
    if (!res.ok) {
      setMessage("Не удалось отправить письмо");
      return;
    }
    setMessage("Письмо отправлено повторно");
    await loadPending(auth);
  };

  const onUpload = async (file: File) => {
    if (!auth) return;
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API_URL}/admin/import`, {
      method: "POST",
      headers: { Authorization: auth },
      body: fd,
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage("Ошибка импорта");
      return;
    }
    setMessage(`Импорт: ${data.imported} добавлено, ${data.skipped} пропущено`);
    await loadStock(auth);
  };

  const exportCsv = async (masked: boolean) => {
    if (!auth) return;
    const res = await fetch(
      `${API_URL}/admin/stock/export?mask_codes=${masked ? "1" : "0"}&full=${masked ? "0" : "1"}`,
      {
        headers: masked ? { Authorization: auth } : { Authorization: auth, "X-Export-Full": "1" },
      }
    );
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "stock-export.csv";
    a.click();
  };

  return (
    <div className="container" style={{ maxWidth: 720 }}>
      <h1>Тестовая СПА продажа — админка</h1>
      <p style={{ fontSize: 14, color: "#666" }}>
        Остатки без полных номеров. Полная выгрузка логируется.
      </p>
      {message && <p className="error">{message}</p>}

      <div style={{ margin: "20px 0" }}>
        <label className="label">Загрузить CSV</label>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
        />
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <button type="button" className="btn btn-secondary" style={{ width: "auto" }} onClick={() => exportCsv(true)}>
          Выгрузка (маска)
        </button>
        <button type="button" className="btn btn-secondary" style={{ width: "auto" }} onClick={() => exportCsv(false)}>
          Полная выгрузка
        </button>
        <button type="button" className="btn btn-secondary" style={{ width: "auto" }} onClick={() => auth && loadStock(auth)}>
          Обновить
        </button>
      </div>

      {pending.length > 0 && (
        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 18 }}>Ожидают отправки PDF</h2>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {pending.map((o) => (
              <li
                key={o.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 0",
                  borderBottom: "1px solid #eee",
                }}
              >
                <span>
                  {o.buyer_email} · {o.nominal_rub} ₽
                </span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ width: "auto", margin: 0 }}
                  onClick={() => retryDelivery(o.id)}
                >
                  Повторить отправку
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #ccc" }}>
            <th>Тип</th>
            <th>Номинал</th>
            <th>Доступно</th>
            <th>Резерв</th>
            <th>Продано</th>
          </tr>
        </thead>
        <tbody>
          {stock.map((r) => (
            <tr key={r.denomination_id} style={{ borderBottom: "1px solid #eee" }}>
              <td>{r.variant}</td>
              <td>{r.nominal_rub} ₽</td>
              <td>{r.available}</td>
              <td>{r.reserved}</td>
              <td>{r.sold}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
