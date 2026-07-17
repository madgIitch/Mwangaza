export function registerServiceWorker(): void {
  if (!("serviceWorker" in navigator) || import.meta.env.MODE !== "production") {
    return;
  }
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js", { scope: "/" });
  });
}
