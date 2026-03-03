const SESSION_KEY = "testforge_session_id";

function getSessionId(): string | null {
  return sessionStorage.getItem(SESSION_KEY);
}

function setSessionId(id: string) {
  sessionStorage.setItem(SESSION_KEY, id);
}

function headers(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const sid = getSessionId();
  if (sid) h["X-Session-Id"] = sid;
  return h;
}

function saveSession(data: { session_id?: string }) {
  if (data.session_id) setSessionId(data.session_id);
}

export async function apiPost<T = unknown>(
  path: string,
  body: Record<string, unknown> = {}
): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data = await res.json();
  saveSession(data);
  return data as T;
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await fetch(path, { headers: headers() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data = await res.json();
  saveSession(data);
  return data as T;
}

export interface SSECallbacks {
  onText?: (text: string) => void;
  onToolCall?: (name: string, input: Record<string, unknown>) => void;
  onToolResult?: (name: string, result: string) => void;
  onDone?: () => void;
}

export async function apiSSE(
  path: string,
  body: Record<string, unknown>,
  callbacks: SSECallbacks
): Promise<void> {
  const res = await fetch(path, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });

  const sid = res.headers.get("X-Session-Id");
  if (sid) setSessionId(sid);

  if (!res.ok || !res.body) throw new Error(`${res.status} ${res.statusText}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let eventType = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6));
        switch (eventType) {
          case "text":
            callbacks.onText?.(data.text);
            break;
          case "tool_call":
            callbacks.onToolCall?.(data.name, data.input);
            break;
          case "tool_result":
            callbacks.onToolResult?.(data.name, data.result);
            break;
          case "done":
            callbacks.onDone?.();
            break;
        }
        eventType = "";
      }
    }
  }

  callbacks.onDone?.();
}
