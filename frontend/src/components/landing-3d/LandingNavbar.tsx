'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowRight, Menu, X } from 'lucide-react';
import { TrackMeldEmblem } from './TrackMeldEmblem';

interface LandingNavbarProps {
  onRequestDemo: () => void;
}

export const LandingNavbar: React.FC<LandingNavbarProps> = ({ onRequestDemo }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Close mobile navigation drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobileMenuOpen]);

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-[#1E293B]/60 bg-[#04070D]/85 backdrop-blur-md px-4 sm:px-8 xl:px-12 flex items-center justify-between">
        {/* Brand Identity */}
        <div className="flex items-center gap-3 shrink-0">
          <Link href="/" className="flex items-center gap-2.5 group">
            <TrackMeldEmblem className="w-8 h-8 transition-transform group-hover:scale-105 shrink-0" />
            <div className="flex flex-col">
              <span className="font-extrabold text-sm tracking-tight text-[#F8FAFC]">
                TRACK<span className="text-[#38BDF8]">MELD</span>
              </span>
              <span className="text-[9px] font-mono tracking-wider text-[#64748B] uppercase">
                RAILWAY DIGITAL TWIN
              </span>
            </div>
          </Link>
        </div>

        {/* Desktop Navigation Links (hidden on tablet/mobile < 1280px to prevent logo collision) */}
        <nav className="hidden xl:flex items-center gap-6 2xl:gap-7 text-xs font-mono text-[#94A3B8]">
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

        {/* Action Buttons + Mobile Hamburger */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          <Link
            href="/planning"
            className="hidden sm:inline-flex items-center text-xs font-mono text-[#94A3B8] hover:text-[#F8FAFC] px-3 py-1.5 rounded border border-[#1E293B] hover:border-[#38BDF8]/40 transition-all bg-[#080D1A]"
          >
            OPERATOR WORKSTATION
          </Link>

          <button
            onClick={onRequestDemo}
            className="px-3.5 py-1.5 rounded bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold tracking-wide transition-all shadow-md shadow-blue-600/30 flex items-center gap-1.5 shrink-0"
          >
            <span>REQUEST DEMO</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>

          {/* Hamburger button for screens < 1280px */}
          <button
            onClick={() => setIsMobileMenuOpen((prev) => !prev)}
            className="xl:hidden p-1.5 rounded-lg text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36] border border-[#1E2D4A] transition-colors"
            aria-label="Toggle navigation menu"
            aria-expanded={isMobileMenuOpen}
          >
            {isMobileMenuOpen ? <X className="w-5 h-5 text-[#38BDF8]" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Responsive Slide-Over Menu for Tablet/Mobile (< 1280px) */}
      {isMobileMenuOpen && (
        <div className="fixed inset-x-0 top-16 z-50 bg-[#070B14]/98 backdrop-blur-xl border-b border-[#1E2D4A] p-5 shadow-2xl xl:hidden flex flex-col gap-3 font-sans animate-in fade-in slide-in-from-top-2 duration-150">
          <nav className="flex flex-col gap-1 text-xs font-mono text-[#94A3B8]">
            <a
              href="#digital-twin"
              onClick={() => setIsMobileMenuOpen(false)}
              className="py-2.5 px-3 rounded-lg hover:bg-[#141F36] hover:text-[#F8FAFC] transition-colors"
            >
              DIGITAL TWIN
            </a>
            <a
              href="#constraints"
              onClick={() => setIsMobileMenuOpen(false)}
              className="py-2.5 px-3 rounded-lg hover:bg-[#141F36] hover:text-[#F8FAFC] transition-colors"
            >
              CONSTRAINTS
            </a>
            <a
              href="#optimization"
              onClick={() => setIsMobileMenuOpen(false)}
              className="py-2.5 px-3 rounded-lg hover:bg-[#141F36] hover:text-[#F8FAFC] transition-colors"
            >
              CP-SAT ENGINE
            </a>
            <a
              href="#validation"
              onClick={() => setIsMobileMenuOpen(false)}
              className="py-2.5 px-3 rounded-lg hover:bg-[#141F36] hover:text-[#F8FAFC] transition-colors"
            >
              VALIDATION
            </a>
            <a
              href="#copilot"
              onClick={() => setIsMobileMenuOpen(false)}
              className="py-2.5 px-3 rounded-lg hover:bg-[#141F36] hover:text-[#F8FAFC] transition-colors"
            >
              AI COPILOT
            </a>
            <a
              href="#comparison"
              onClick={() => setIsMobileMenuOpen(false)}
              className="py-2.5 px-3 rounded-lg hover:bg-[#141F36] hover:text-[#F8FAFC] transition-colors"
            >
              PLAN COMPARISON
            </a>
          </nav>
          <div className="pt-3 border-t border-[#1E2D4A] flex flex-col gap-2">
            <Link
              href="/planning"
              onClick={() => setIsMobileMenuOpen(false)}
              className="flex items-center justify-center text-xs font-mono text-[#38BDF8] py-2.5 rounded-lg border border-[#2D436D] bg-[#0E1726] hover:bg-[#141F36] transition-colors"
            >
              OPERATOR WORKSTATION
            </Link>
            <button
              onClick={() => {
                setIsMobileMenuOpen(false);
                onRequestDemo();
              }}
              className="w-full py-2.5 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-md shadow-blue-600/30 transition-colors"
            >
              <span>REQUEST DEMO</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </>
  );
};
