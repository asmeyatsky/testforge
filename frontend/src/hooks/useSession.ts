import { createContext, useContext } from "react";

export interface SessionContextValue {
  sessionId: string | null;
}

export const SessionContext = createContext<SessionContextValue>({
  sessionId: null,
});

export function useSession() {
  return useContext(SessionContext);
}
