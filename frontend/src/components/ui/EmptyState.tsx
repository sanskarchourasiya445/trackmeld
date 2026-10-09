'use client';

import React from 'react';
import { LucideIcon, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  actionVariant?: 'default' | 'outline' | 'secondary';
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = HelpCircle,
  title,
  description,
  actionLabel,
  onAction,
  actionVariant = 'default',
  secondaryActionLabel,
  onSecondaryAction,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center bg-[#0B101C] border border-[#1E2D4A] rounded-xl select-none ${className}`}
    >
      <div className="w-12 h-12 rounded-xl bg-[#141F36] border border-[#2D436D] flex items-center justify-center mb-4 text-[#38BDF8]">
        <Icon className="w-6 h-6" />
      </div>

      <h3 className="text-base font-bold text-[#F8FAFC] tracking-tight mb-1.5">
        {title}
      </h3>

      <p className="text-xs text-[#94A3B8] max-w-md leading-relaxed mb-6 font-sans">
        {description}
      </p>

      {(actionLabel || secondaryActionLabel) && (
        <div className="flex items-center gap-3">
          {actionLabel && onAction && (
            <Button
              size="sm"
              variant={actionVariant}
              onClick={onAction}
              className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold px-4 h-8"
            >
              {actionLabel}
            </Button>
          )}

          {secondaryActionLabel && onSecondaryAction && (
            <Button
              size="sm"
              variant="outline"
              onClick={onSecondaryAction}
              className="border-[#2D436D] text-[#CBD5E1] hover:text-white text-xs h-8 px-4"
            >
              {secondaryActionLabel}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
