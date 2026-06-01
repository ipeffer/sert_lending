# Платёжка и фискальный чек

## Рекомендация: ЮKassa + ОФД

1. Зарегистрировать магазин в [ЮKassa](https://yookassa.ru).
2. Подключить онлайн-кассу (54-ФЗ) в личном кабинете — чек уходит на email покупателя автоматически при успешной оплате.
3. В `.env` задать:

```env
PAYMENT_PROVIDER=yookassa
YOOKASSA_SHOP_ID=ваш_shop_id
YOOKASSA_SECRET_KEY=ваш_secret_key
YOOKASSA_RETURN_URL=https://cert.k8.ru/payment/success
```

4. В личном кабинете ЮKassa указать URL webhook:

```
https://cert.k8.ru/api/webhooks/yookassa
```

5. Для локальной отладки используйте [ngrok](https://ngrok.com) или сначала `PAYMENT_PROVIDER=mock`.

## Тест без договора

```env
PAYMENT_PROVIDER=mock
```

После «оплаты» пользователь перенаправляется на success URL; webhook вызывается автоматически с сервера.

## Проверка

- Создать заказ с фронта → перейти на mock/yookassa → убедиться, что код перешёл в `sold` и письмо ушло (или заказ в `paid_pending_delivery`).
