import React, { useState, useRef, useEffect } from "react";
import { Send, Mic, MicOff } from "lucide-react";

interface Props {
  onSendMessage: (text: string) => void;
  muted: boolean;
  onToggleMute: (next: boolean) => void;
  disabled?: boolean;
}

export function ChatInput({ onSendMessage, muted, onToggleMute, disabled }: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (text.trim()) {
      onSendMessage(text);
      setText("");
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea heights
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }, [text]);

  return (
    <div className="flex items-end gap-2 rounded-xl border border-hairline bg-surface/50 p-2 focus-within:border-amber/40 focus-within:ring-1 focus-within:ring-amber/20 backdrop-blur-md">
      {/* Microphone Mute Button */}
      <button
        type="button"
        onClick={() => onToggleMute(!muted)}
        disabled={disabled}
        className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg border transition-all ${
          muted
            ? "border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/15"
            : "border-hairline bg-surface-raised text-ink-soft hover:bg-surface-raised/85 hover:text-ink"
        }`}
        title={muted ? "Mikrofonu Aç (M)" : "Mikrofonu Kapat (M)"}
      >
        {muted ? <MicOff size={14} strokeWidth={2} /> : <Mic size={14} strokeWidth={2} />}
      </button>

      {/* Input Field */}
      <textarea
        ref={textareaRef}
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Bir komut yazın veya sorun..."
        disabled={disabled}
        className="flex-1 resize-none bg-transparent px-1 py-1 font-mono text-[11.5px] leading-relaxed text-ink placeholder-ink-muted focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 max-h-[120px] min-h-[24px]"
      />

      {/* Send Button */}
      <button
        type="button"
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg transition-all ${
          text.trim()
            ? "amber-glow bg-amber text-obsidian hover:bg-amber-glow"
            : "bg-surface-raised text-ink-faint cursor-not-allowed"
        }`}
        title="Gönder (Enter)"
      >
        <Send size={12} strokeWidth={2.5} fill={text.trim() ? "currentColor" : "none"} />
      </button>
    </div>
  );
}
