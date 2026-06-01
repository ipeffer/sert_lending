"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  OrderStatus,
  certificateDownloadUrl,
  fetchOrderStatus,
} from "@/lib/api";

function SuccessInner() {
  const params = useSearchParams();
  const token = params.get("token");
  const [order, setOrder] = useState<OrderStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("Не указан номер заказа");
      return;
    }
    let attempts = 0;
    const poll = () => {
      fetchOrderStatus(token)
        .then((o) => {
          setOrder(o);
          if (
            o.can_download_certificate ||
            o.status === "paid" ||
            o.status === "paid_pending_delivery" ||
            attempts >= 8
          ) {
            return;
          }
          attempts += 1;
          setTimeout(poll, 500);
        })
        .catch(() => setError("Не удалось загрузить статус заказа"));
    };
    poll();
  }, [token]);

  return (
    <div className="container" style={{ textAlign: "center", paddingTop: 48 }}>
      <h1 style={{ color: "var(--brand)" }}>Спасибо за покупку!</h1>

      {error && <p className="error">{error}</p>}

      {!error && !order && <p>Проверяем оплату…</p>}

      {order && (
        <>
          <p style={{ marginTop: 16 }}>
            Сертификат на <strong>{order.nominal_rub.toLocaleString("ru-RU")} ₽</strong>
            {order.certificate_delivered
              ? " отправлен на "
              : " готов. Письмо на "}
            <strong>{order.buyer_email}</strong>
            {order.certificate_delivered ? "." : " (SMTP не настроен — скачайте PDF ниже)."}
          </p>

          {order.can_download_certificate && token && (
            <a
              href={certificateDownloadUrl(token)}
              className="btn btn-primary"
              style={{ display: "inline-flex", marginTop: 24, maxWidth: 320, textDecoration: "none" }}
            >
              Скачать PDF сертификата
            </a>
          )}

          <p style={{ fontSize: 13, color: "#666", marginTop: 24 }}>
            Фискальный чек при боевой оплате приходит от платёжной системы на email.
            <br />
            В тестовом режиме используется имитация оплаты.
          </p>
        </>
      )}

      <p style={{ marginTop: 32 }}>
        <a href="/">Купить ещё один сертификат</a>
      </p>
    </div>
  );
}

export default function PaymentSuccessPage() {
  return (
    <Suspense>
      <SuccessInner />
    </Suspense>
  );
}
