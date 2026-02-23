import React from "react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/app/providers/theme";

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <Button
      variant="outline"
      className="rounded-full bg-background/80 shadow-sm backdrop-blur"
      onClick={toggle}
      title="Toggle theme"
    >
      {theme === "dark" ? "🌙 Dark" : "🌞 Light"}
    </Button>
  );
}
