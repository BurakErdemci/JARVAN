import { useState } from "react";
import { Mic, MicOff, CornerDownLeft } from "lucide-react";

interface Props {
  onSendMessage: (text: string) => void;
  muted: boolean;
  onToggleMute: (v: boolean) => void;
  disabled?: boolean;
}

/** Komut girişi — terminal prompt havasında tek satır + mikrofon anahtarı. */
export function CommandInput({ onSendMessage, muted, onToggleMute, disabled }: Props) {
  const [text, setText] = useState("");

  const submit = () => {
    const t = text.trim();
    if (!t) return;
    onSendMessage(t);
    setText("");
  };

  return (
    <div className="chamfer flex items-center gap-2 border border-steel bg-hull-sunken px-3 py-2">
      <span className="font-mono text-[13px] text-coolant" aria-hidden="true">▸</span>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder={disabled ? "hat kapalı — backend bekleniyor" : "komut yaz…"}
        disabled={disabled}
        className="min-w-0 flex-1 bg-transparent font-mono text-[13px] text-ink placeholder:text-ink-ghost focus:outline-none disabled:opacity-40"
      />
      <button
        onClick={submit}
        disabled={disabled || !text.trim()}
        title="Gönder (Enter)"
        className="p-1 text-ink-ghost transition-colors hover:text-coolant disabled:opacity-30"
      >
        <CornerDownLeft size={15} />
      </button>
      <span className="h-4 w-px bg-steel" aria-hidden="true" />
      <button
        onClick={() => onToggleMute(!muted)}
        disabled={disabled}
        title={muted ? "Mikrofonu aç (M)" : "Mikrofonu sustur (M)"}
        className="p-1 transition-colors disabled:opacity-30"
        style={{ color: muted ? "#FF4D5E" : "#43E5C9" }}
      >
        {muted ? <MicOff size={15} /> : <Mic size={15} />}
      </button>
    </div>
  );
}
