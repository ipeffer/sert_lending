# Подключение к spa.k8.ru (Tilda)

Страница [spa.k8.ru/certificate](https://spa.k8.ru/certificate) сейчас встраивает `https://spa2.k8.ru/certificate`.

## Шаги для владельца сайта

1. Развернуть сервис `k8-certificates` на поддомене, например **`https://cert.k8.ru`** (DNS A/AAAA на VPS, TLS в Caddy).
2. В редакторе Tilda на странице `/certificate` найти блок **HTML** с iframe.
3. Заменить `src`:

```html
<iframe
  src="https://cert.k8.ru/?iframe=1"
  width="100%"
  height="600"
  frameborder="0"
  style="border:0; width:100%; min-height: 500px; overflow: hidden;"
  id="k8-certificate-iframe"
  title="Покупка подарочного сертификата"
></iframe>
<script>
  window.addEventListener('message', function (event) {
    if (event.data && event.data.type === 'resize' && event.data.height) {
      var iframe = document.getElementById('k8-certificate-iframe');
      if (iframe) iframe.style.height = event.data.height + 'px';
    }
    if (event.data === 'scroll_to_top') {
      var iframe = document.getElementById('k8-certificate-iframe');
      if (iframe) {
        var offset = iframe.getBoundingClientRect().top + window.scrollY - 100;
        window.scrollTo({ top: offset, behavior: 'smooth' });
      }
    }
  });
</script>
```

4. В `.env` бэкенда добавить в `CORS_ORIGINS`: `https://spa.k8.ru`.
5. Проверить покупку в тестовом режиме (`PAYMENT_PROVIDER=mock`), затем переключить на `yookassa`.

## CSP (если используется)

На `cert.k8.ru` в ответах должен быть заголовок:

```
Content-Security-Policy: frame-ancestors 'self' https://spa.k8.ru https://tilda.cc;
```

Это уже настроено в Next.js (`next.config.ts`).

## Альтернатива

Если подрядчик отдаст доступ к **spa2**, можно перенести только API пула кодов в существующий Strapi и не менять iframe.
