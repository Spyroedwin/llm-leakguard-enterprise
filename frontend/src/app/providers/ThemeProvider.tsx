import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type Theme = "light" | "dark" | "system";

type ThemeContextValue = {
  theme: Theme;
  resolvedTheme: "light" | "dark";
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemTheme(): "light" | "dark" {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

const STORAGE_KEY = "leakguard:theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Theme | null;
    return saved ?? "system";
  });

  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Theme | null;
    if (saved === "dark" || saved === "light") return saved;
    return typeof window !== "undefined" ? getSystemTheme() : "light";
  });

  useEffect(() => {
    const root = document.documentElement;

    const apply = () => {
      const next = theme === "system" ? getSystemTheme() : theme;
      setResolvedTheme(next);

      root.classList.toggle("dark", next === "dark");
    };

    apply();

    if (theme !== "system") {
      localStorage.setItem(STORAGE_KEY, theme);
      return;
    }

    // system mode: follow OS changes
    localStorage.setItem(STORAGE_KEY, "system");
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => apply();
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, [theme]);

  const value = useMemo<ThemeContextValue>(() => {
    return {
      theme,
      resolvedTheme,
      setTheme: (t) => setThemeState(t),
      toggleTheme: () =>
        setThemeState((prev) => (prev === "dark" ? "light" : "dark")),
    };
  }, [theme, resolvedTheme]);

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}
