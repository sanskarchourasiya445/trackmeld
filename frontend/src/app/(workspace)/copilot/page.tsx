'use client';

import React from 'react';
import { CopilotWorkspace } from '@/components/planning/CopilotWorkspace';
import { Bot, ShieldAlert } from 'lucide-react';

export default function CopilotPage() {
  return (
    <>
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden p-2 sm:p-2.5 lg:p-3 gap-2 bg-[#04070D] font-sans max-w-[1920px] w-full mx-auto select-none">
        {/* Workspace Operational Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 bg-[#0B101C] border border-[#1E2D4A] rounded-lg px-3.5 py-2 shrink-0 shadow-sm">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#38BDF8]">
                <Bot className="w-4 h-4" />
              </div>
              <h1 className="text-base font-bold text-[#F8FAFC]">AI Decision Support Copilot</h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#2563EB]/20 text-[#93C5FD] border border-[#2563EB]/30 font-bold">
                READ-ONLY EXPLAINER
              </span>
            </div>
            <p className="text-[11px] text-[#94A3B8] mt-0.5">
              Causal explanation of optimization choices, constraint violations, and schedule alternatives with exact evidence citations
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono bg-[#0F172A] border border-[#1E2D4A] px-2.5 py-1 rounded-md text-[#CBD5E1]">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>Zero write-tools • Does NOT schedule trains</span>
          </div>
        </div>

        {/* Embedded Full Copilot Workspace Surface */}
        <div className="flex-1 min-h-0 bg-[#0B101C] border border-[#1E2D4A] rounded-lg overflow-hidden shadow-sm flex flex-col">
          <CopilotWorkspace hideHeader={true} />
        </div>
      </div>
    </>
  );
}
