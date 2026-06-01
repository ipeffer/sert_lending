"use client";

export function TestModeBanner() {
  if (process.env.NEXT_PUBLIC_SHOW_TEST_BANNER !== "true") {
    return null;
  }
  return (
    <div
      style={{
        background: "#fff3cd",
        color: "#664d03",
        padding: "10px 16px",
        fontSize: 14,
        textAlign: "center",
        borderBottom: "1px solid #ffc107",
      }}
    >
      Тестовая СПА продажа · демо-стенд · оплата имитируется
    </div>
  );
}
