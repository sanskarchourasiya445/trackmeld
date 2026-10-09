'use client';

import React from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

interface AlertBannerProps {
  variant?: 'info' | 'warning' | 'danger' | 'success';
  title?: string;
  message: string | React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({
  variant = 'info',
  title,
  message,
  actionLabel,
  onAction,
  onDismiss,
  className = '',
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'danger':
        return {
          container: 'bg-rose-500/10 border-rose-500/30 text-rose-300',
          icon: <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />,
          actionBtn: 'text-rose-400 hover:text-rose-200 border-rose-500/40',
        };
      case 'warning':
        return {
          container: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
          icon: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />,
          actionBtn: 'text-amber-400 hover:text-amber-200 border-amber-500/40',
        };
      case 'success':
        return {
          container: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
          icon: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />,
          actionBtn: 'text-emerald-400 hover:text-emerald-200 border-emerald-500/40',
        };
      case 'info':
      default:
        return {
          container: 'bg-[#141F36] border-[#2563EB]/40 text-[#93C5FD]',
          icon: <Info className="w-4 h-4 text-[#38BDF8] shrink-0" />,
          actionBtn: 'text-[#38BDF8] hover:text-white border-[#2D436D]',
        };
    }
  };

  const styles = getVariantStyles();

  return (
    <div
      className={`border rounded-lg px-3.5 py-2.5 flex items-center justify-between gap-3 text-xs font-sans ${styles.container} ${className}`}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        {styles.icon}
        <div className="min-w-0 leading-relaxed">
          {title && <span className="font-bold mr-1.5 text-[#F8FAFC]">{title}</span>}
          <span>{message}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold border transition-colors ${styles.actionBtn}`}
          >
            {actionLabel}
          </button>
        )}

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 text-[#94A3B8] hover:text-white rounded transition-colors"
            title="Dismiss notice"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
