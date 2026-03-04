import { useEffect, useState } from "react";

export interface ToastMessage {
  id: number;
  text: string;
  type: "success" | "error" | "info";
}

let _nextId = 0;
let _listener: ((msg: ToastMessage) => void) | null = null;

export function showToast(text: string, type: ToastMessage["type"] = "success") {
  _listener?.({ id: _nextId++, text, type });
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    _listener = (msg) => setToasts((prev) => [...prev, msg]);
    return () => {
      _listener = null;
    };
  }, []);

  useEffect(() => {
    if (toasts.length === 0) return;
    const timer = setTimeout(() => {
      setToasts((prev) => prev.slice(1));
    }, 3000);
    return () => clearTimeout(timer);
  }, [toasts]);

  const colors = {
    success: "bg-green-600",
    error: "bg-red-600",
    info: "bg-blue-600",
  };

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`${colors[t.type]} text-white px-4 py-2 rounded shadow-lg text-sm animate-fade-in`}
        >
          {t.text}
        </div>
      ))}
    </div>
  );
}
