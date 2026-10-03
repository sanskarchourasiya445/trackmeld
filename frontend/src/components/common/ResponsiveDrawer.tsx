'use client';

import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ResponsiveDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
  maxWidth?: string; // e.g. 'max-w-md', 'max-w-lg', 'max-w-xl'
  position?: 'right' | 'bottom'; // defaults to responsive: bottom on mobile, right on tablet/desktop
}

export const ResponsiveDrawer: React.FC<ResponsiveDrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  badge,
  children,
  maxWidth = 'max-w-md',
}) => {
  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex select-none">
      {/* 1. Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity duration-200"
        aria-hidden="true"
      />

      {/* 2. Drawer Panel (Bottom Sheet on mobile < md, Slide-over on >= md) */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`fixed z-50 flex flex-col bg-[#0F172A] border-[#1E2D4A] shadow-2xl transition-all duration-300 ease-out
          bottom-0 inset-x-0 max-h-[88dvh] rounded-t-xl border-t
          md:bottom-0 md:top-0 md:right-0 md:left-auto md:max-h-full md:rounded-none md:border-l md:border-t-0 md:w-full ${maxWidth}
        `}
      >
        {/* Mobile handle indicator */}
        <div className="w-12 h-1 bg-[#334155] rounded-full mx-auto my-2 md:hidden" />

        {/* Drawer Header */}
        <div className="h-12 bg-[#141F36] border-b border-[#1E2D4A] px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-semibold text-xs sm:text-sm text-[#F8FAFC] truncate">
              {title}
            </span>
            {badge && <div className="shrink-0">{badge}</div>}
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={onClose}
              className="p-1.5 rounded text-[#94A3B8] hover:text-white hover:bg-[#1E2D4A] transition-colors"
              title="Close"
              aria-label="Close dialog"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {subtitle && (
          <div className="px-4 py-1.5 bg-[#0A0E17]/60 border-b border-[#1E2D4A] text-[11px] text-[#94A3B8]">
            {subtitle}
          </div>
        )}

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {children}
        </div>
      </div>
    </div>
  );
};
