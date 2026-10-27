import { useState, useRef, useCallback, useEffect } from "react";
import { api } from "./api";

export function useResource<T>(path: string, interval = 5000) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState("");
  const currentPath = useRef(path);
  currentPath.current = path;
  const refresh = useCallback(async () => {
    try {
      const result = await api<T>(path);
      if (currentPath.current !== path) return;
      setData(result);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [path]);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (!document.hidden) void refresh();
    }, interval);
    return () => clearInterval(timer);
  }, [refresh, interval]);
  return { data, error, refresh };
}
