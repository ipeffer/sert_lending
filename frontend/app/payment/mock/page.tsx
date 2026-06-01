"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { getApiUrl } from "@/lib/api";

function MockPaymentInner() {
  const params = useSearchParams();
  const orderId = params.get("order");
  const token = params.get("token");
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    if (!orderId) {
      setStatus("error");
      return;
    }
    fetch(`${getApiUrl()}/api/webhooks/mock/${orderId}`, { method: "POST" })
      .then((r) => {
        if (!r.ok) throw new Error("webhook failed");
        const q = token ? `?token=${encodeURIComponent(token)}` : "";
        window.location.href = `/payment/success${q}`;
      })
      .catch(() => setStatus("error"));
  }, [orderId, token]);

  return (
    <div className="container" style={{ textAlign: "center", paddingTop: 48 }}>
      {status === "loading" && <p>Имитация оплаты…</p>}
      {status === "error" && (
        <>
          <p className="error">Ошибка тестовой оплаты</p>
          <p style={{ marginTop: 16 }}>
            <a href="/">Вернуться к форме</a>
          </p>
        </>
      )}
    </div>
  );
}

export default function MockPaymentPage() {
  return (
    <Suspense>
      <MockPaymentInner />
    </Suspense>
  );
}
