import { useState } from "react";
import { X, Copy, Check, AlertTriangle, AlertOctagon, CornerRightDown, ArrowLeft, Clock } from "lucide-react";
import type { TaskInfo } from "../types";

interface Props {
  task: TaskInfo;
  onClose: () => void;
}

export function TaskDetail({ task, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (task.result) {
      navigator.clipboard.writeText(task.result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const steps = task.steps || [];

  return (
    <div className="flex h-full flex-col overflow-hidden bg-surface-sunken/40">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-hairline bg-surface/50 px-3 py-2">
        <button
          onClick={onClose}
          className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-ink-muted transition-colors hover:text-ink"
        >
          <ArrowLeft size={11} />
          <span>listeye dön</span>
        </button>
        <button
          onClick={onClose}
          className="grid h-5 w-5 place-items-center rounded-md border border-hairline bg-surface/20 text-ink-muted transition-all hover:bg-surface-raised hover:text-ink"
          title="Kapat"
        >
          <X size={11} />
        </button>
      </div>

      {/* Detail Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Title & Metadata */}
        <div>
          <div className="flex items-center gap-2 font-mono text-[9px]">
            <span className="rounded bg-surface-sunken border border-hairline px-1.5 py-0.5 text-ink-soft uppercase tracking-wider">
              {task.target}
            </span>
            <span className="text-ink-faint">ID: #{task.id}</span>
          </div>
          <h3 className="mt-1.5 font-mono text-[14px] font-semibold text-ink leading-snug">
            {task.title}
          </h3>
        </div>

        {/* Live status banner */}
        {task.detail && (
          <div className="rounded-lg border border-hairline bg-surface-raised/40 p-2.5 font-mono text-[10.5px] leading-relaxed text-ink-soft flex items-start gap-2">
            <CornerRightDown size={12} className="text-amber mt-0.5" />
            <div>
              <span className="text-ink-faint mr-1.5">Mevcut Durum:</span>
              <span className="text-ink">{task.detail}</span>
            </div>
          </div>
        )}

        {/* Blocked or Error Callouts */}
        {task.status === "blocked" && task.error && (
          <div className="rounded-lg border border-amber/30 bg-amber/5 p-3 font-mono text-[10.5px] leading-relaxed text-ink shadow-[0_0_12px_rgba(255,138,61,0.06)]">
            <div className="flex items-center gap-2 text-amber font-semibold uppercase tracking-wider text-[9.5px]">
              <AlertTriangle size={12} />
              <span>GÖREV BLOKE OLDU</span>
            </div>
            <p className="mt-2 text-amber/90 select-text font-medium">{task.error}</p>
            <div className="mt-2 border-t border-amber/10 pt-2 text-[9px] text-ink-muted">
              💡 <span className="font-semibold text-ink-soft">Öneri:</span> Sorunu çözüp veya komutla ajanı yönlendirebilirsiniz.
            </div>
          </div>
        )}

        {task.status === "error" && task.error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3 font-mono text-[10.5px] leading-relaxed text-ink shadow-[0_0_12px_rgba(239,68,68,0.06)]">
            <div className="flex items-center gap-2 text-red-400 font-semibold uppercase tracking-wider text-[9.5px]">
              <AlertOctagon size={12} />
              <span>HATA ALINDI</span>
            </div>
            <p className="mt-2 text-red-400/90 select-text font-medium">{task.error}</p>
          </div>
        )}

        {/* Steps Timeline */}
        <div className="space-y-2">
          <span className="font-mono text-[9px] uppercase tracking-wider text-ink-faint">
            Adım Geçmişi ({steps.length})
          </span>

          {steps.length === 0 ? (
            <div className="rounded-lg border border-hairline/50 p-3 text-center font-mono text-[9.5px] text-ink-faint">
              Adım günlüğü bulunmuyor.
            </div>
          ) : (
            <div className="relative border-l border-hairline/60 ml-2 pl-3 py-1 space-y-3">
              {steps.map((step, idx) => (
                <div key={idx} className="relative group">
                  {/* Timeline dot */}
                  <span className="absolute -left-[16px] top-1 h-[7px] w-[7px] rounded-full border border-surface bg-ink-muted" />

                  {/* Step details */}
                  <div className="flex flex-col">
                    <span className="font-mono text-[9.5px] leading-relaxed text-ink select-text">
                      {step.text}
                    </span>
                    <span className="font-mono text-[8px] text-ink-faint flex items-center gap-0.5 mt-0.5">
                      <Clock size={8} />
                      {new Date(step.ts).toLocaleTimeString("tr-TR", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Result Output Area */}
        {task.result && (
          <div className="flex flex-col rounded-lg border border-hairline bg-surface/50 overflow-hidden">
            {/* Action Bar */}
            <div className="flex items-center justify-between border-b border-hairline bg-surface/80 px-2.5 py-1.5 font-mono text-[9px]">
              <span className="text-ink-soft uppercase tracking-wider">Görev Çıktısı</span>
              <button
                onClick={handleCopy}
                className={`flex items-center gap-1 rounded px-1.5 py-0.5 border border-hairline bg-surface transition-all ${
                  copied
                    ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/5"
                    : "text-ink-soft hover:bg-surface-raised hover:text-ink"
                }`}
              >
                {copied ? <Check size={9} /> : <Copy size={9} />}
                <span>{copied ? "Kopyalandı!" : "Kopyala"}</span>
              </button>
            </div>

            {/* Code view */}
            <div className="p-3 overflow-x-auto bg-surface-sunken/90 font-mono text-[10px] leading-[1.6] select-text">
              <pre className="whitespace-pre text-ink-soft">{task.result}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
