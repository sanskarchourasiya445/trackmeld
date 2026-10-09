'use client';

import React, { useState } from 'react';
import { Terminal, MessageSquare } from 'lucide-react';

export const SectionCopilot: React.FC = () => {
  const [selectedPromptIdx, setSelectedPromptIdx] = useState<number>(0);

  const samplePrompts = [
    {
      query: "Why can't TSK-0007 start at 13:40 UTC on SEC-12?",
      answer: `ANALYSIS: Task TSK-0007 (Track Regrading) cannot begin at 13:40 UTC due to hard temporal conflicts:

1. TRAIN CONFLICT: Express Rake 02073 (Vande Bharat) enters block section SEC-12 at 13:48 UTC (UP MAIN).
2. BUFFER VIOLATION: Required safety setup buffer of 10.0 minutes is infringed by 2.0 minutes.
3. ADJACENT IMPACT: TSK-0007 requires AdjacentTrackImpact = CAUTION_ORDER (45 km/h) which is currently blocked by commercial headway.

RECOMMENDED NEXT WINDOW: 14:20 — 16:10 UTC (Feasible, 0 conflicts, Validated).`,
      toolUsed: 'get_task_decision(task_id="TSK-0007")',
      status: 'DIAGNOSTIC EVIDENCE RETURNED',
    },
    {
      query: 'What conflicts with train EXPRESS-07 across corridor?',
      answer: `RETRIEVAL FOR TRAIN: 12004 (EXPRESS-07) across corridor NDLS-GZB-ALJN:

1. SECTION SEC-03 (km 14.2): Contention with planned possession S-04 (P-Way Tamping).
   - Resolved by CP-SAT: Shifted possession to 16:25 UTC (+18.4 min headway safety margin).
2. SECTION SEC-07 (km 88.0): OHE Power Isolation FS-02 ends at 05:40 UTC. Train scheduled arrival is 06:12 UTC (Clear).

OVERALL IMPACT: 0 commercial delay minutes introduced by maintenance schedule.`,
      toolUsed: 'get_conflicts_for_task(train_id="12004")',
      status: 'SCHEDULE SANITY CERTIFIED',
    },
    {
      query: 'What changes if block section S-04 is unavailable?',
      answer: `WHAT-IF SENSITIVITY EVALUATION:
If section S-04 is declared unavailable (Emergency Speed Restriction / Track Defect):

- IMPACTED TASKS: TSK-0007 and TSK-0012
- SHIFT ALTERNATIVE: Relocated to alternate corridor segment SEC-14 (km 42.1)
- DELAY EXPOSURE: +0 min commercial train delay
- OBJECTIVE PENALTY: Priority score reduced by 14.2 points due to window tightness.

Plan candidate remains strictly feasible under CP-SAT.`,
      toolUsed: 'get_run_summary(scenario_id="SCN-DEMO-001")',
      status: 'RELAXATION ANALYSIS COMPLETED',
    },
    {
      query: 'Approve candidate plan PV-001 and publish to track.',
      answer: `[MUTATION REFUSAL — GOVERNANCE GUARDRAIL ACTIVATED]

ERROR: Copilot is strictly read-only and cannot mutate, approve, or reject schedules.

GOVERNANCE INVARIANT:
- AI Explains, Humans Approve.
- COMPLETED ≠ APPROVED.
- Plan approval requires formal cryptographic sign-off by an authorized OPERATOR under Four-Eyes segregation (plan.created_by != actor.username).

Please access the Four-Eyes Review Drawer in the Operator Workstation to perform authorized approval.`,
      toolUsed: 'REFUSED: check_mutation_refusal(query)',
      status: 'STRICT READ-ONLY REFUSAL',
      isRefusal: true,
    },
  ];

  return (
    <section id="copilot" className="py-24 sm:py-32 px-6 sm:px-12 lg:px-20 border-t border-[#1E293B] bg-[#060A13]">
      <span id="ai-copilot" className="sr-only" />
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#38BDF8] font-bold">
            05 / EXPLANATORY ASSISTANCE
          </div>
          <h2 className="mt-2 text-3xl sm:text-5xl font-extrabold tracking-tight text-[#F8FAFC]">
            AI THAT
            <br />
            <span className="text-[#38BDF8]">EXPLAINS THE PLAN.</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#94A3B8] leading-relaxed">
            AI does not control the schedule. AI helps human operational officers understand the schedule. The Copilot is strictly read-only and queries deterministic diagnostic evidence.
          </p>
        </div>

        {/* Interactive Copilot Workstation Terminal */}
        <div className="mt-16 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Prompt Selector Buttons (Left) */}
          <div className="lg:col-span-5 space-y-3">
            <div className="text-xs font-mono text-[#64748B] uppercase tracking-wider mb-2 font-bold">
              Select Operator Query:
            </div>
            {samplePrompts.map((p, idx) => {
              const isSelected = selectedPromptIdx === idx;
              return (
                <button
                  key={idx}
                  onClick={() => setSelectedPromptIdx(idx)}
                  className={`w-full p-4 rounded-xl text-left border transition-all flex items-start gap-3 ${
                    isSelected
                      ? 'bg-[#0B1426] border-[#38BDF8] shadow-lg shadow-blue-900/30'
                      : 'bg-[#080D1A]/80 border-[#1E293B] hover:border-[#38BDF8]/40 hover:bg-[#0A101F]'
                  }`}
                >
                  <MessageSquare
                    className={`w-4 h-4 mt-0.5 shrink-0 ${
                      p.isRefusal
                        ? 'text-rose-400'
                        : isSelected
                        ? 'text-[#38BDF8]'
                        : 'text-[#64748B]'
                    }`}
                  />
                  <div className="flex-1">
                    <div className="text-xs sm:text-sm font-semibold text-[#F1F5F9] leading-snug">
                      &ldquo;{p.query}&rdquo;
                    </div>
                    <div className="text-[10px] font-mono text-[#64748B] mt-1.5 flex items-center justify-between">
                      <span>{p.isRefusal ? 'MUTATION GUARDRAIL' : 'TYPED QUERY TOOL'}</span>
                      <span className={p.isRefusal ? 'text-rose-400 font-bold' : 'text-[#38BDF8]'}>
                        {isSelected ? 'ACTIVE' : 'SELECT →'}
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Terminal Output Window (Right) */}
          <div className="lg:col-span-7 bg-[#04070D] border border-[#1E293B] rounded-xl overflow-hidden shadow-2xl">
            {/* Terminal Header Bar */}
            <div className="px-5 py-3 bg-[#080D1A] border-b border-[#1E293B] flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-[#38BDF8]" />
                <span className="text-[#F1F5F9] font-bold">TRACKMELD COPILOT ENGINE</span>
              </div>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                  samplePrompts[selectedPromptIdx].isRefusal
                    ? 'bg-rose-500/20 text-rose-400'
                    : 'bg-emerald-500/20 text-emerald-400'
                }`}
              >
                {samplePrompts[selectedPromptIdx].status}
              </span>
            </div>

            {/* Terminal Body */}
            <div className="p-6 font-mono text-xs text-[#E2E8F0] space-y-4">
              {/* Operator Prompt */}
              <div className="text-[#94A3B8] pb-3 border-b border-[#1E293B]">
                <span className="text-[#38BDF8] font-bold">OPERATOR &gt; </span>
                {samplePrompts[selectedPromptIdx].query}
              </div>

              {/* Tool Execution Stamp */}
              <div className="text-[10px] text-[#64748B] bg-[#080D18] p-2 rounded border border-[#1E293B]/60">
                <span className="text-[#38BDF8] font-bold">GROUNDED TOOL: </span>
                {samplePrompts[selectedPromptIdx].toolUsed}
              </div>

              {/* Engine Answer */}
              <div
                className={`p-4 rounded-lg whitespace-pre-wrap leading-relaxed ${
                  samplePrompts[selectedPromptIdx].isRefusal
                    ? 'bg-[#1C0E14] border border-rose-500/30 text-rose-200'
                    : 'bg-[#080D1A] border border-[#1E293B] text-[#CBD5E1]'
                }`}
              >
                {samplePrompts[selectedPromptIdx].answer}
              </div>

              {/* Bottom Assurance */}
              <div className="pt-2 text-[10px] text-[#64748B] flex items-center justify-between border-t border-[#1E293B]/60">
                <span>EVIDENCE SOURCE: REPOSITORIES & DIAGNOSTICS</span>
                <span className="text-emerald-400 font-bold">ZERO HALLUCINATED APPROVALS</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
