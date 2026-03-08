import { useState } from "react";
import { api } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function LogsDialog() {
  const [text, setText] = useState<string>("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const t = await api.logs();
      setText(typeof t === "string" ? t : JSON.stringify(t, null, 2));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" onClick={load}>
          /logs
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Logs</DialogTitle>
        </DialogHeader>
        <pre className="max-h-[70vh] overflow-auto rounded-lg border p-3 text-xs">
          {loading ? "Loading..." : text || "No logs. Yet. 😈"}
        </pre>
      </DialogContent>
    </Dialog>
  );
}
