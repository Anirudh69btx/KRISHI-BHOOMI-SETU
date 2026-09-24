import React, { useState } from "react";
import { AlertTriangle, Volume2, VolumeX, X } from "lucide-react";

interface DisasterAlertProps {
  type: string;
  severity: "ADVISORY" | "WATCH" | "WARNING" | "EMERGENCY";
  title: string;
  titleHi?: string;
  message: string;
  messageHi?: string;
  onDismiss?: () => void;
}

export const DisasterBanner: React.FC<DisasterAlertProps> = ({
  type,
  severity,
  title,
  titleHi,
  message,
  messageHi,
  onDismiss,
}) => {
  const [sirenActive, setSirenActive] = useState(false);
  const [lang, setLang] = useState<"en" | "hi">("en");

  const isEmergency = severity === "EMERGENCY" || severity === "WARNING";

  const toggleSiren = () => {
    setSirenActive((prev) => !prev);
    // In production, triggers Web Audio API oscillation or play siren audio asset
  };

  return (
    <div
      className={`w-full p-4 mb-4 rounded-xl border transition-all ${
        isEmergency
          ? "bg-red-950/80 border-red-500/50 text-red-100 shadow-lg shadow-red-950/50"
          : "bg-amber-950/80 border-amber-500/50 text-amber-100"
      }`}
      role="alert"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${isEmergency ? "bg-red-800 text-white animate-pulse" : "bg-amber-800 text-white"}`}>
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-black/40">
                {severity} • {type}
              </span>
              <button
                onClick={() => setLang(lang === "en" ? "hi" : "en")}
                className="text-xs underline hover:text-white transition-colors"
              >
                {lang === "en" ? "हिंदी में देखें" : "View in English"}
              </button>
            </div>
            <h3 className="font-semibold text-base mt-1">
              {lang === "hi" && titleHi ? titleHi : title}
            </h3>
            <p className="text-sm opacity-90 mt-0.5">
              {lang === "hi" && messageHi ? messageHi : message}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isEmergency && (
            <button
              onClick={toggleSiren}
              className={`p-2 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition-colors ${
                sirenActive
                  ? "bg-red-600 text-white border-red-400 animate-bounce"
                  : "bg-red-900/50 border-red-700/50 hover:bg-red-800/60"
              }`}
              title="Toggle Audio Siren Alert"
            >
              {sirenActive ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
              <span>{sirenActive ? "Siren Active" : "Test Siren"}</span>
            </button>
          )}

          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
