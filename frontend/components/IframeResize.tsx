"use client";

import { useEffect } from "react";

export function IframeResize() {
  useEffect(() => {
    const isIframe = window.self !== window.top;
    if (!isIframe) return;

    document.documentElement.classList.add("is-iframe");

    const sendHeight = () => {
      window.parent.postMessage(
        { type: "resize", height: document.documentElement.scrollHeight },
        "*"
      );
    };

    const observer = new ResizeObserver(sendHeight);
    observer.observe(document.documentElement);
    window.addEventListener("load", sendHeight);
    sendHeight();

    return () => {
      observer.disconnect();
      window.removeEventListener("load", sendHeight);
    };
  }, []);

  return null;
}
