import { useState, type FormEvent } from "react";
import type { SendResult } from "../types";

interface Props {
  busy: boolean;
  onSend: (text: string) => Promise<SendResult>;
}

export function Composer({ busy, onSend }: Props) {
  const [value, setValue] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    const text = value.trim();
    if (!text || busy) return;
    setValue("");
    const result = await onSend(text);
    // Keep the user's words on failure (unless they've already typed something new).
    if (result === "failed") setValue((cur) => (cur === "" ? text : cur));
  }

  return (
    <form className="cp-composer" onSubmit={submit}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search products, check a SKU…"
        aria-label="Message"
        autoComplete="off"
      />
      <button type="submit" className="cp-send" disabled={busy || !value.trim()}>
        Send
      </button>
    </form>
  );
}
