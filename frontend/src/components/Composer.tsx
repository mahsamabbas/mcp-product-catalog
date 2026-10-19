import { useState, type FormEvent } from "react";

interface Props {
  busy: boolean;
  onSend: (text: string) => void;
}

export function Composer({ busy, onSend }: Props) {
  const [value, setValue] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = value.trim();
    if (!text || busy) return;
    onSend(text);
    setValue("");
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
