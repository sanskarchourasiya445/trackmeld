'use client';

import React from 'react';
import Link from 'next/link';
import { TrainTrack, ArrowRight } from 'lucide-react';

interface LandingNavbarProps {
  onRequestDemo: () => void;
}

export const LandingNavbar: React.FC<LandingNavbarProps> = ({ onRequestDemo }) => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-[#1E293B]/60 bg-[#04070D]/80 backdrop-blur-md px-6 sm:px-12 flex items-center justify-between">
      {/* Brand Identity */}
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded bg-[#0F172A] border border-[#2563EB]/40 group-hover:border-[#38BDF8] transition-colors flex items-center justify-center shadow-lg shadow-blue-900/20">
            <TrainTrack className="w-4 h-4 text-[#38BDF8]" />
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-sm tracking-tight text-[#F8FAFC]">
              TRACKMELD
            </span>
            <span className="text-[9px] font-mono tracking-wider text-[#64748B] uppercase">
              RAILWAY DIGITAL TWIN
            </span>
          </div>
        </Link>
      </div>

      {/* Navigation Links */}
      <nav className="hidden md:flex items-center gap-7 text-xs font-mono text-[#94A3B8]">
        <a href="#digital-twin" className="hover:text-[#F8FAFC] transition-colors">
          DIGITAL TWIN
        </a>
        <a href="#constraints" className="hover:text-[#F8FAFC] transition-colors">
          CONSTRAINTS
        </a>
        <a href="#optimization" className="hover:text-[#F8FAFC] transition-colors">
          CP-SAT ENGINE
        </a>
        <a href="#validation" className="hover:text-[#F8FAFC] transition-colors">
          VALIDATION
        </a>
        <a href="#copilot" className="hover:text-[#F8FAFC] transition-colors">
          AI COPILOT
        </a>
        <a href="#comparison" className="hover:text-[#F8FAFC] transition-colors">
          PLAN COMPARISON
        </a>
      </nav>

      {/* Action Buttons */}
      <div className="flex items-center gap-3">
        <Link
          href="/planning"
          className="hidden sm:inline-flex items-center text-xs font-mono text-[#94A3B8] hover:text-[#F8FAFC] px-3 py-1.5 rounded border border-[#1E293B] hover:border-[#38BDF8]/40 transition-all bg-[#080D1A]"
        >
          OPERATOR WORKSTATION
        </Link>

        <button
          onClick={onRequestDemo}
          className="px-3.5 py-1.5 rounded bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold tracking-wide transition-all shadow-md shadow-blue-600/30 flex items-center gap-1.5"
        >
          <span>REQUEST DEMO</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
