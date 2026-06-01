"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Catalog,
  NominalOption,
  createOrder,
  fetchCatalog,
} from "@/lib/api";

type Step = 1 | 2;

const PRIVACY_URL = "https://spa.k8.ru/privacy";
const PD_URL = "https://spa.k8.ru/personal-data";

export function CertificateForm() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [variant, setVariant] = useState<"spa" | "ar">("spa");
  const [denominationId, setDenominationId] = useState<number | "">("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [consentPd, setConsentPd] = useState(false);
  const [consentPrivacy, setConsentPrivacy] = useState(false);
  const [step, setStep] = useState<Step>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCatalog()
      .then(setCatalog)
      .catch((e) => setError(e.message));
  }, []);

  const nominals: NominalOption[] = useMemo(() => {
    if (!catalog) return [];
    return variant === "spa" ? catalog.spa_nominals : catalog.ar_nominals;
  }, [catalog, variant]);

  const selected = nominals.find((n) => n.id === denominationId);

  useEffect(() => {
    const first = nominals.find((n) => n.can_buy);
    if (first && denominationId === "") setDenominationId(first.id);
    else if (selected && !selected.can_buy) {
      const alt = nominals.find((n) => n.can_buy);
      setDenominationId(alt?.id ?? "");
    }
  }, [nominals, denominationId, selected]);

  const canProceedStep1 =
    selected?.can_buy &&
    name.trim().length >= 2 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) &&
    phone.replace(/\D/g, "").length >= 10;

  const canPay = consentPd && consentPrivacy;

  const goConfirm = () => {
    setError(null);
    if (!canProceedStep1) {
      setError("Заполните все поля корректно");
      return;
    }
    setStep(2);
    if (window.self !== window.top) {
      window.parent.postMessage("scroll_to_top", "*");
    }
  };

  const submitOrder = useCallback(async () => {
    if (!selected || !canPay) return;
    setLoading(true);
    setError(null);
    try {
      const result = await createOrder({
        denomination_id: selected.id,
        buyer_name: name.trim(),
        buyer_email: email.trim(),
        buyer_phone: phone.trim(),
        consent_pd: consentPd,
        consent_privacy: consentPrivacy,
      });
      window.location.href = result.redirect_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
      setLoading(false);
    }
  }, [selected, canPay, name, email, phone, consentPd, consentPrivacy]);

  const variantLabel = variant === "spa" ? "Тестовая СПА продажа" : "Адмиральский разряд";

  return (
    <div className="container">
      <div className="steps">
        <div className={`step ${step >= 1 ? "active" : ""}`} />
        <div className={`step ${step >= 2 ? "active" : ""}`} />
      </div>

      <div className="card-preview">
        <div style={{ fontSize: 14, opacity: 0.9 }}>{variantLabel}</div>
        <div className="nominal">
          {selected ? `${selected.nominal_rub.toLocaleString("ru-RU")} ₽` : "—"}
        </div>
      </div>

      <div className="variant-tabs">
        <button
          type="button"
          className={variant === "spa" ? "active" : ""}
          onClick={() => {
            setVariant("spa");
            setDenominationId("");
          }}
        >
          Тестовая СПА продажа
        </button>
        <button
          type="button"
          className={variant === "ar" ? "active" : ""}
          onClick={() => {
            setVariant("ar");
            setDenominationId("");
          }}
        >
          Адмиральский разряд
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {step === 1 && (
        <>
          <div className="field">
            <label className="label" htmlFor="nominal">
              Номинал сертификата
            </label>
            <select
              id="nominal"
              value={denominationId}
              onChange={(e) => setDenominationId(Number(e.target.value))}
            >
              {nominals.length === 0 && <option value="">Нет доступных номиналов</option>}
              {nominals.map((n) => (
                <option key={n.id} value={n.id} disabled={!n.can_buy}>
                  {n.nominal_rub.toLocaleString("ru-RU")} ₽
                  {!n.can_buy ? " — нет в наличии" : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="label" htmlFor="name">
              Ваше имя *
            </label>
            <input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Иван"
              autoComplete="name"
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="email">
              Email *
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="mail@example.com"
              autoComplete="email"
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="phone">
              Телефон *
            </label>
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+7 (4012) 000-00-00"
              autoComplete="tel"
            />
          </div>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!canProceedStep1}
            onClick={goConfirm}
          >
            Далее
          </button>
        </>
      )}

      {step === 2 && selected && (
        <>
          <h2 style={{ fontSize: 20, marginBottom: 16 }}>Подтверждение заказа</h2>
          <div className="summary-row">
            <span>Сертификат</span>
            <span>
              {variantLabel}, {selected.nominal_rub.toLocaleString("ru-RU")} ₽
            </span>
          </div>
          <div className="summary-row">
            <span>Имя</span>
            <span>{name}</span>
          </div>
          <div className="summary-row">
            <span>Email</span>
            <span>{email}</span>
          </div>
          <div className="summary-row">
            <span>Телефон</span>
            <span>{phone}</span>
          </div>
          <div className="summary-row">
            <span>К оплате</span>
            <strong>{selected.price_rub.toLocaleString("ru-RU")} ₽</strong>
          </div>

          <label className="checkbox">
            <input
              type="checkbox"
              checked={consentPd}
              onChange={(e) => setConsentPd(e.target.checked)}
            />
            <span>
              Согласен на{" "}
              <a href={PD_URL} target="_blank" rel="noreferrer">
                обработку персональных данных
              </a>
            </span>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={consentPrivacy}
              onChange={(e) => setConsentPrivacy(e.target.checked)}
            />
            <span>
              Ознакомлен с{" "}
              <a href={PRIVACY_URL} target="_blank" rel="noreferrer">
                политикой конфиденциальности
              </a>
            </span>
          </label>

          <button
            type="button"
            className="btn btn-primary"
            disabled={!canPay || loading}
            onClick={submitOrder}
          >
            {loading ? "Переход к оплате…" : "Перейти к оплате"}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setStep(1)}
            disabled={loading}
          >
            Изменить
          </button>
        </>
      )}
    </div>
  );
}
