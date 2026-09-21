import QRCode from "qrcode";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

const POLL_INTERVAL_MS = 2000;

/** Telegram QR login: shows a `tg://login?token=...` QR code and polls the
 * backend until the user confirms it in the Telegram app. See AGENTS.md 4.1
 * for the caveats (untested against live Telegram servers, DC migration
 * restarts the flow instead of following it seamlessly). */
export default function QrLogin({ onSuccess }) {
  const canvasRef = useRef(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("starting");

  useEffect(() => {
    let cancelled = false;
    let requestId = null;
    let timer = null;

    async function drawQr(url) {
      if (canvasRef.current) {
        await QRCode.toCanvas(canvasRef.current, url, { width: 220, margin: 1 });
      }
    }

    async function start() {
      try {
        const res = await api.qrStart();
        if (cancelled) return;
        requestId = res.request_id;
        await drawQr(res.qr_url);
        setStatus("pending");
        poll();
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    async function poll() {
      if (cancelled || !requestId) return;
      try {
        const res = await api.qrPoll(requestId);
        if (cancelled) return;

        if (res.status === "success") {
          setStatus("success");
          onSuccess?.(res.account);
          return;
        }
        if (res.status === "restart") {
          setStatus("starting");
          start();
          return;
        }
        if (res.qr_url) await drawQr(res.qr_url);
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    start();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [onSuccess]);

  return (
    <div className="flex flex-col items-center gap-3 py-2">
      <div className="rounded-xl bg-white p-3">
        <canvas ref={canvasRef} width={220} height={220} />
      </div>
      <p className="text-sm text-slate-400 text-center max-w-xs">
        Откройте Telegram на телефоне → Настройки → Устройства → Подключить устройство и
        отсканируйте код
      </p>
      {status === "starting" && <p className="text-xs text-slate-500">Генерация кода…</p>}
      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  );
}
