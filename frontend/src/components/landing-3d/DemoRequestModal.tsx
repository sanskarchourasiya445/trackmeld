'use client';

import React, { useState, useEffect } from 'react';
import { X, CheckCircle2, ShieldCheck, ArrowRight, Loader2, Download, Building2, User, Mail, Network } from 'lucide-react';

interface DemoRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DemoRequestModal: React.FC<DemoRequestModalProps> = ({ isOpen, onClose }) => {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    organization: '',
    role: 'Possession Planning Manager',
    networkScale: '500 - 2,000 Route KM',
    focusArea: 'Minimizing Possession Overruns & Conflict Resolution'
  });

  const [status, setStatus] = useState<'idle' | 'submitting' | 'success'>('idle');
  const [requestReference, setRequestReference] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('submitting');
    setTimeout(() => {
      const randomRef = `TM-REQ-${Math.floor(1000 + Math.random() * 9000)}-VERIFIED`;
      setRequestReference(randomRef);
      setStatus('success');
    }, 1200);
  };

  const handleReset = () => {
    setStatus('idle');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-md transition-opacity"
        onClick={status === 'submitting' ? undefined : onClose}
      />

      {/* Modal Dialog Card */}
      <div className="relative w-full max-w-xl rounded-2xl border border-slate-700/80 bg-[#070a11] text-slate-200 shadow-2xl p-6 sm:p-8 z-10 overflow-hidden">
        {/* Ambient Top Glow */}
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-64 h-32 bg-sky-500/15 blur-3xl pointer-events-none" />

        {/* Close Button */}
        <button
          onClick={onClose}
          disabled={status === 'submitting'}
          className="absolute top-5 right-5 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {status === 'success' ? (
          /* SUCCESS STATE */
          <div className="py-6 text-center">
            <div className="w-14 h-14 mx-auto mb-5 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-lg shadow-emerald-500/10">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-slate-800 border border-slate-700 text-xs font-mono text-slate-300 mb-3">
              REFERENCE TOKEN: <span className="text-sky-400 font-bold">{requestReference}</span>
            </div>

            <h3 className="text-2xl font-bold text-white mb-2">
              Architecture Dossier Scheduled
            </h3>
            
            <p className="text-slate-400 text-sm max-w-md mx-auto mb-6 leading-relaxed">
              Thank you, <strong className="text-slate-200">{formData.fullName}</strong>. Our rail systems engineering team will transmit the complete TrackMeld mathematical optimization specification and governance whitepaper to <strong className="text-sky-400">{formData.email}</strong>.
            </p>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 text-left text-xs font-mono space-y-2 mb-6">
              <div className="text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800 pb-2 flex items-center justify-between">
                <span>Verification Package Inclusions</span>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-slate-300">✓ 13-Rule Independent Safety Firewall Verification Matrix</div>
              <div className="text-slate-300">✓ CP-SAT Discrete Interval Benchmark Performance Logs</div>
              <div className="text-slate-300">✓ Four-Eyes Immutable Sign-Off Governance Architecture</div>
              <div className="text-slate-300">✓ Synthetic Meso-Topology Reproducibility Seed Catalog</div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleReset}
                className="flex-1 py-3 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold text-sm transition-all shadow-md cursor-pointer"
              >
                Return to Digital Twin
              </button>
              <button
                onClick={() => {
                  alert(`Demonstration dossier TM-2026-ARCH.pdf download simulation initiated for ${formData.email}`);
                }}
                className="inline-flex items-center justify-center gap-2 py-3 px-4 rounded-lg border border-slate-700 hover:border-slate-500 text-slate-300 hover:text-white text-sm font-medium transition-all"
              >
                <Download className="w-4 h-4 text-sky-400" />
                <span>Executive Summary (PDF)</span>
              </button>
            </div>
          </div>
        ) : (
          /* FORM STATE */
          <div>
            <div className="mb-6">
              <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded border border-sky-500/30 bg-sky-950/40 text-sky-400 text-[11px] font-mono uppercase tracking-wider mb-2">
                ENTERPRISE EVALUATION
              </div>
              <h3 className="text-2xl font-bold text-white tracking-tight">
                Schedule Architecture Briefing
              </h3>
              <p className="text-slate-400 text-xs mt-1">
                Receive private access to our technical benchmark reports, solver formulation details, and sandbox environments.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1.5 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-sky-400" />
                  <span>Full Name</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.fullName}
                  onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                  placeholder="e.g. Dr. Elena Vance"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-800 bg-slate-900/90 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1.5 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-sky-400" />
                    <span>Work Email</span>
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="name@railway.gov / .com"
                    className="w-full px-3.5 py-2.5 rounded-lg border border-slate-800 bg-slate-900/90 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1.5 flex items-center gap-1.5">
                    <Building2 className="w-3.5 h-3.5 text-sky-400" />
                    <span>Organization / Authority</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.organization}
                    onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                    placeholder="e.g. Central Corridor Rail"
                    className="w-full px-3.5 py-2.5 rounded-lg border border-slate-800 bg-slate-900/90 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1.5">
                    Operational Role
                  </label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-slate-800 bg-slate-900/90 text-white text-sm focus:outline-none focus:border-sky-500 transition-colors cursor-pointer"
                  >
                    <option value="Possession Planning Manager">Possession Planning Manager</option>
                    <option value="Infrastructure Director">Infrastructure Maintenance Director</option>
                    <option value="Safety & Compliance Auditor">Safety & Compliance Auditor</option>
                    <option value="Signalling / Interlocking Lead">Signalling / Interlocking Lead</option>
                    <option value="Timetable Dispatch Lead">Timetable Dispatch Lead</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1.5 flex items-center gap-1.5">
                    <Network className="w-3.5 h-3.5 text-sky-400" />
                    <span>Network Scale</span>
                  </label>
                  <select
                    value={formData.networkScale}
                    onChange={(e) => setFormData({ ...formData, networkScale: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-slate-800 bg-slate-900/90 text-white text-sm focus:outline-none focus:border-sky-500 transition-colors cursor-pointer"
                  >
                    <option value="< 500 Route KM">&lt; 500 Route KM (Regional / Metro)</option>
                    <option value="500 - 2,000 Route KM">500 – 2,000 Route KM (Corridor)</option>
                    <option value="> 2,000 Route KM">&gt; 2,000 Route KM (National Network)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1.5">
                  Primary Evaluation Focus
                </label>
                <select
                  value={formData.focusArea}
                  onChange={(e) => setFormData({ ...formData, focusArea: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-800 bg-slate-900/90 text-white text-sm focus:outline-none focus:border-sky-500 transition-colors cursor-pointer"
                >
                  <option value="Minimizing Possession Overruns & Conflict Resolution">
                    Possession Conflict Resolution & Overrun Reduction
                  </option>
                  <option value="Independent Safety Rule Enforcement & Auditability">
                    13-Category Safety Rule Enforcement & Auditability
                  </option>
                  <option value="CP-SAT Mathematical Optimization Performance">
                    CP-SAT Solver Integration & Heuristic Performance
                  </option>
                  <option value="Four-Eyes Governance & Human Sign-off Workflow">
                    Four-Eyes Approval Governance & Role Separation
                  </option>
                </select>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={status === 'submitting'}
                  className="w-full py-3.5 px-4 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-sky-500/20 flex items-center justify-center gap-2 cursor-pointer"
                >
                  {status === 'submitting' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Validating Enterprise Request...</span>
                    </>
                  ) : (
                    <>
                      <span>Transmit Architecture Request</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="text-[11px] text-center text-slate-500 font-mono">
                🔒 Protected by TrackMeld Enterprise Privacy Protocol. No spam, ever.
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
