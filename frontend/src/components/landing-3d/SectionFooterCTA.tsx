'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, ShieldCheck, Terminal, Cpu, FileText, CheckCircle2 } from 'lucide-react';

interface SectionFooterCTAProps {
  onOpenDemo: () => void;
}

export const SectionFooterCTA: React.FC<SectionFooterCTAProps> = ({ onOpenDemo }) => {
  return (
    <footer className="relative bg-[#05070a] border-t border-slate-800/80 text-slate-300 pt-24 pb-16 overflow-hidden">
      {/* Background Subtle Track Pattern */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: 'repeating-linear-gradient(90deg, #38bdf8 0, #38bdf8 1px, transparent 1px, transparent 60px), repeating-linear-gradient(0deg, #38bdf8 0, #38bdf8 1px, transparent 1px, transparent 60px)'
        }}
      />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-64 bg-radial-gradient from-sky-500/10 via-transparent to-transparent blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Main CTA Hero Box */}
        <div className="relative rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 via-[#090d16]/80 to-[#04060a]/90 p-8 sm:p-14 lg:p-16 mb-20 shadow-2xl overflow-hidden backdrop-blur-xl">
          {/* Subtle Accent Glow */}
          <div className="absolute -top-32 -right-32 w-80 h-80 rounded-full bg-sky-500/10 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-32 -left-32 w-80 h-80 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded border border-sky-500/30 bg-sky-950/40 text-sky-300 text-xs font-mono uppercase tracking-wider mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
              DEPLOYMENT & DEMONSTRATION READY
            </div>

            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-white mb-6 leading-tight">
              Plan the railway. <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-sky-300 to-indigo-300">
                Before it happens.
              </span>
            </h2>

            <p className="text-slate-400 text-base sm:text-lg mb-8 leading-relaxed max-w-2xl">
              Eliminate possession overrun penalties, resolve interlocking conflicts deterministically, 
              and arm planning engineers with mathematical proof of schedule feasibility.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
              <button
                onClick={onOpenDemo}
                className="inline-flex items-center justify-center gap-3 px-7 py-3.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-sky-500/20 hover:shadow-sky-500/35 hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
              >
                <span>Schedule Architecture Briefing</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <Link
                href="/plans"
                className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-lg border border-slate-700 hover:border-slate-500 bg-slate-900/60 hover:bg-slate-800/80 text-white font-medium text-sm transition-all hover:-translate-y-0.5"
              >
                <Terminal className="w-4 h-4 text-sky-400" />
                <span>Launch Operational Sandbox</span>
              </Link>
            </div>

            {/* Key Confidence Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-12 pt-8 border-t border-slate-800/80">
              <div className="flex items-center gap-2.5 text-xs font-mono text-slate-400">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>Four-Eyes Governance Hardened</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs font-mono text-slate-400">
                <Cpu className="w-4 h-4 text-sky-400 shrink-0" />
                <span>CP-SAT Mathematical Feasibility</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs font-mono text-slate-400">
                <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>13 Independent Safety Checks</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Navigation Columns */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 pb-12 border-b border-slate-800/80 text-xs font-mono">
          <div>
            <h4 className="text-white font-semibold tracking-wider uppercase mb-4 text-xs font-mono">
              SYSTEM ARCHITECTURE
            </h4>
            <ul className="space-y-2.5 text-slate-400">
              <li>
                <a href="#digital-twin" className="hover:text-sky-400 transition-colors">
                  Meso-Topology Digital Twin
                </a>
              </li>
              <li>
                <a href="#constraints" className="hover:text-sky-400 transition-colors">
                  Domain Constraint Engine
                </a>
              </li>
              <li>
                <a href="#optimization" className="hover:text-sky-400 transition-colors">
                  CP-SAT Interval Optimization
                </a>
              </li>
              <li>
                <a href="#validation" className="hover:text-sky-400 transition-colors">
                  13-Category Safety Firewall
                </a>
              </li>
              <li>
                <a href="#copilot" className="hover:text-sky-400 transition-colors">
                  Read-Only Grounded AI Copilot
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold tracking-wider uppercase mb-4 text-xs font-mono">
              GOVERNANCE INVARIANTS
            </h4>
            <ul className="space-y-2.5 text-slate-400">
              <li className="text-slate-300">FEASIBLE ≠ APPROVED</li>
              <li className="text-slate-300">VALID ≠ APPROVED</li>
              <li className="text-slate-300">AI EXPLAINS ≠ AI APPROVES</li>
              <li className="text-slate-300">CREATOR ≠ APPROVER</li>
              <li className="text-emerald-400">HUMAN IN THE LOOP MANDATORY</li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold tracking-wider uppercase mb-4 text-xs font-mono">
              VERIFICATION & AUDIT
            </h4>
            <ul className="space-y-2.5 text-slate-400">
              <li>
                <span className="text-slate-500">Suite:</span> 472 Automated Tests
              </li>
              <li>
                <span className="text-slate-500">Validator:</span> Independent Rule Engine
              </li>
              <li>
                <span className="text-slate-500">Provenance:</span> Deterministic Synthetic Data
              </li>
              <li>
                <span className="text-slate-500">Ledger:</span> Immutable Audit Sign-Off
              </li>
              <li>
                <span className="text-slate-500">Build:</span> Next.js 16 + FastAPI
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-semibold tracking-wider uppercase mb-4 text-xs font-mono">
              DOCUMENTATION
            </h4>
            <ul className="space-y-2.5 text-slate-400">
              <li>
                <Link href="/plans" className="hover:text-sky-400 transition-colors inline-flex items-center gap-1">
                  <span>Interactive Application</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </li>
              <li>
                <a 
                  href="https://github.com/sanskarchourasiya445/Trackmeld" 
                  target="_blank" 
                  rel="noreferrer"
                  className="hover:text-sky-400 transition-colors inline-flex items-center gap-1"
                >
                  <FileText className="w-3 h-3" />
                  <span>GitHub Repository</span>
                </a>
              </li>
              <li>
                <button 
                  onClick={onOpenDemo}
                  className="hover:text-sky-400 transition-colors text-left"
                >
                  Request Technical Whitepaper
                </button>
              </li>
            </ul>
          </div>
        </div>

        {/* Regulatory & Safety Operational Boundary Notice */}
        <div className="mt-8 pt-6 pb-6 text-[11px] leading-relaxed text-slate-300 font-mono border-b border-slate-800/80">
          <p className="mb-2">
            <strong className="text-amber-400">SAFETY BOUNDARY NOTICE:</strong> TrackMeld is an enterprise decision-support, constraint-verification, and mathematical schedule optimization prototype. All possession schedules, track closure envelopes, power de-energization requests, and isolation permits require formal human sign-off under strict four-eyes operational governance. TrackMeld does NOT directly command physical interlocking systems, axle counters, or vital signalling relays.
          </p>
          <p className="text-slate-300">
            Topology networks, train movements, and maintenance work orders displayed in this digital-twin demonstration are generated under reproducible deterministic synthetic seeds for evaluation purposes.
          </p>
        </div>

        {/* Bottom Bar: Copyright & System Status */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-slate-300">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-slate-300 font-medium">TRACKMELD PLATFORM</span>
            <span className="text-slate-400">|</span>
            <span className="text-slate-300">PHASE 21 PORTFOLIO RELEASE</span>
          </div>

          <div className="text-slate-300 text-center sm:text-right">
            © 2026 TrackMeld Railway Systems. Deterministic synthetic provenance.
          </div>
        </div>
      </div>
    </footer>
  );
};
