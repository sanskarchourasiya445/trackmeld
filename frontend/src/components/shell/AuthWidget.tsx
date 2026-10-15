'use client';

/**
 * AuthWidget — Token-based authentication entry widget for TrackMeld.
 *
 * Design constraints:
 * - Token is NEVER displayed after entry (password-type input only).
 * - No credentials are hardcoded.
 * - "Authenticated" state only means the token was accepted by an API call;
 *   it does NOT fabricate a username or role since no /auth/me endpoint exists.
 * - 401 from any route → unauthenticated state.
 * - 403 → authenticated but forbidden (role insufficient).
 * - Token stored in sessionStorage (per-tab, cleared on close).
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Lock, LogOut, CheckCircle2, AlertCircle, Loader2, KeyRound, X } from 'lucide-react';
import { getAuthToken, setAuthToken, API_BASE_URL } from '@/lib/api/client';

type AuthState =
  | 'unauthenticated'
  | 'verifying'
  | 'authenticated'
  | 'forbidden'
  | 'error';

async function verifyToken(token: string): Promise<'authenticated' | 'forbidden' | 'error'> {
  try {
    const res = await fetch(`${API_BASE_URL}/planning-runs?limit=1`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok || res.status === 200) return 'authenticated';
    if (res.status === 403) return 'forbidden';
    if (res.status === 401) return 'error';
    // Any 2xx or non-auth error: treat as authenticated (token accepted)
    if (res.status < 500) return 'authenticated';
    return 'error';
  } catch {
    return 'error';
  }
}

export function AuthWidget() {
  const [state, setState] = useState<AuthState>(() =>
    getAuthToken() ? 'authenticated' : 'unauthenticated'
  );
  const [isOpen, setIsOpen] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Re-sync state if another tab clears the token
  useEffect(() => {
    const onStorage = () => {
      setState(getAuthToken() ? 'authenticated' : 'unauthenticated');
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  // Close panel on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && (state === 'unauthenticated' || state === 'error')) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen, state]);

  const handleSignIn = useCallback(async () => {
    const raw = tokenInput.trim();
    if (!raw) {
      setErrorMsg('Token is required.');
      return;
    }
    setErrorMsg(null);
    setState('verifying');
    const result = await verifyToken(raw);
    if (result === 'authenticated') {
      setAuthToken(raw);
      setTokenInput('');
      setState('authenticated');
      setIsOpen(false);
    } else if (result === 'forbidden') {
      // Token was accepted but role is insufficient for that endpoint
      setAuthToken(raw);
      setTokenInput('');
      setState('forbidden');
      setIsOpen(false);
    } else {
      setState('error');
      setErrorMsg('Token rejected (401). Check the value and try again.');
    }
  }, [tokenInput]);

  const handleSignOut = useCallback(() => {
    setAuthToken(null);
    setTokenInput('');
    setErrorMsg(null);
    setState('unauthenticated');
    setIsOpen(false);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSignIn();
    if (e.key === 'Escape') setIsOpen(false);
  };

  const badgeConfig = {
    unauthenticated: {
      label: 'Sign In',
      color: 'text-[#94A3B8] hover:text-white',
      dot: 'bg-zinc-500',
      icon: <Lock className="w-3 h-3" />,
    },
    verifying: {
      label: 'Verifying…',
      color: 'text-amber-400',
      dot: 'bg-amber-400 animate-pulse',
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
    },
    authenticated: {
      label: 'Authenticated',
      color: 'text-emerald-400',
      dot: 'bg-emerald-400',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    forbidden: {
      label: 'Restricted',
      color: 'text-amber-300',
      dot: 'bg-amber-400',
      icon: <AlertCircle className="w-3 h-3" />,
    },
    error: {
      label: 'Auth Failed',
      color: 'text-rose-400',
      dot: 'bg-rose-400',
      icon: <AlertCircle className="w-3 h-3" />,
    },
  } as const;

  const cfg = badgeConfig[state];

  return (
    <div className="relative" ref={panelRef}>
      {/* Trigger operator profile button */}
      <button
        onClick={() => setIsOpen((p) => !p)}
        className="flex items-center gap-2 p-1 pl-1.5 pr-2 rounded-lg hover:bg-[#111A2E] border border-transparent hover:border-[#1E304E] transition-all focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none cursor-pointer"
        title="Operator Session & Authentication"
        aria-label={`Authentication: ${cfg.label}`}
      >
        <div className="relative">
          <div className="w-7 h-7 rounded-full bg-[#162544] border border-[#233A6B] flex items-center justify-center text-[11px] font-bold text-[#38BDF8] shrink-0">
            OP
          </div>
          <span className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-[#080C14] ${cfg.dot}`} />
        </div>
        <div className="hidden md:flex flex-col text-left leading-tight">
          <span className="text-xs font-semibold text-[#F8FAFC]">Operator</span>
          <span className={`text-[10px] font-medium ${cfg.color}`}>{cfg.label}</span>
        </div>
        <div className="hidden lg:block ml-0.5">
          {cfg.icon}
        </div>
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-[#0F172A] border border-[#1E2D4A] rounded-lg shadow-xl z-50 text-xs">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-[#1E2D4A]">
            <div className="flex items-center gap-1.5 text-[#F8FAFC] font-semibold">
              <KeyRound className="w-3.5 h-3.5 text-[#3B82F6]" />
              TrackMeld Authentication
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-[#64748B] hover:text-white transition-colors"
              aria-label="Close"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="p-3 space-y-3">
            {/* Current status */}
            <div className="flex items-center gap-2 text-[11px]">
              <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
              <span className={cfg.color}>{cfg.label}</span>
              {state === 'authenticated' && (
                <span className="text-[#64748B] ml-auto">Token active (session)</span>
              )}
              {state === 'forbidden' && (
                <span className="text-[#64748B] ml-auto">Token accepted, role restricted</span>
              )}
            </div>

            {/* Show sign-in form when not successfully authenticated */}
            {(state === 'unauthenticated' || state === 'error' || state === 'verifying') && (
              <>
                <div className="space-y-1.5">
                  <label className="text-[#94A3B8] block">API Token</label>
                  <input
                    ref={inputRef}
                    type="password"
                    value={tokenInput}
                    onChange={(e) => { setTokenInput(e.target.value); setErrorMsg(null); }}
                    onKeyDown={handleKeyDown}
                    placeholder="Bearer token…"
                    autoComplete="current-password"
                    disabled={state === 'verifying'}
                    className="w-full bg-[#0A0E17] border border-[#2D436D] rounded px-2.5 py-2 text-[#F8FAFC] placeholder-[#334155] focus:outline-none focus:border-[#3B82F6] disabled:opacity-50 font-mono"
                  />
                </div>

                {errorMsg && (
                  <p className="text-rose-400 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3 shrink-0" />
                    {errorMsg}
                  </p>
                )}

                <button
                  onClick={handleSignIn}
                  disabled={state === 'verifying' || !tokenInput.trim()}
                  className="w-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-50 text-white font-semibold rounded py-1.5 transition-colors flex items-center justify-center gap-1.5"
                >
                  {state === 'verifying' ? (
                    <><Loader2 className="w-3 h-3 animate-spin" /> Verifying…</>
                  ) : (
                    <><Lock className="w-3 h-3" /> Sign In</>
                  )}
                </button>
              </>
            )}

            {/* Sign out when authenticated or forbidden */}
            {(state === 'authenticated' || state === 'forbidden') && (
              <>
                <p className="text-[#64748B] text-[10px]">
                  Token stored in sessionStorage (cleared on tab close).
                  It is never displayed after entry.
                </p>
                <button
                  onClick={handleSignOut}
                  className="w-full border border-[#334155] hover:border-rose-500/40 text-[#94A3B8] hover:text-rose-400 font-medium rounded py-1.5 transition-colors flex items-center justify-center gap-1.5"
                >
                  <LogOut className="w-3 h-3" />
                  Clear token / Sign out
                </button>
              </>
            )}

            <p className="text-[10px] text-[#334155] border-t border-[#1E2D4A] pt-2">
              TrackMeld uses Bearer token auth. No username or role is inferred
              from the token — identity is authoritative on the backend only.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
