'use client';

import React from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { CopilotWorkspace } from '@/components/planning/CopilotWorkspace';
import { Bot, ShieldAlert, Sparkles, HelpCircle } from 'lucide-react';

export default function CopilotPage() {
  return (
    <AppShell
      activeScenarioId="SCN-DEMO-001"
      scenarioName="Northern Trunk Corridor (NDLS - CNB)"
      planningHorizon="Copilot: Read-Only Decision Support"
      tasksCount={29}
      trainsCount={50}
    >
      <div className="flex-1 flex flex-col h-full overflow-hidden p-4 sm:p-6 lg:p-7 gap-4 bg-[#04070D] font-sans max-w-[1900px] w-full mx-auto select-none">
        {/* Workspace Operational Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0B101C] border border-[#1E2D4A] rounded-xl px-5 py-3.5 shrink-0 shadow-lg">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#38BDF8]">
                <Bot className="w-4 h-4" />
              </div>
              <h1 className="text-lg font-bold text-[#F8FAFC]">AI Decision Support Copilot</h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#2563EB]/20 text-[#93C5FD] border border-[#2563EB]/30 font-bold">
                READ-ONLY EXPLAINER
              </span>
            </div>
            <p className="text-xs text-[#94A3B8] mt-1">
              Causal explanation of optimization choices, constraint violations, and schedule alternatives with exact evidence citations
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono bg-[#0F172A] border border-[#1E2D4A] px-3 py-1.5 rounded-lg text-[#CBD5E1]">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>Zero write-tools • Does NOT schedule trains</span>
          </div>
        </div>

        {/* Embedded Full Copilot Workspace Surface */}
        <div className="flex-1 min-h-0 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden shadow-sm">
          <CopilotWorkspace hideHeader={true} />
        </div>
      </div>
    </AppShell>
  );
}
