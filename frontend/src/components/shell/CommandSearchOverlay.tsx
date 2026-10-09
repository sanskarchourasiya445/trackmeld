'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  Train,
  Wrench,
  TrainTrack,
  Radio,
  Zap,
  AlertTriangle,
  ShieldCheck,
  FileText,
  X,
  ArrowRight,
  CornerDownLeft,
} from 'lucide-react';
import {
  CORRIDOR_STATIONS_GIS,
  CORRIDOR_SECTIONS_GIS,
  CORRIDOR_SIGNALS_GIS,
  CORRIDOR_OHE_POSTS_GIS,
  ACTIVE_TRAINS_GIS,
} from '@/lib/railway/corridorGisData';
import { DEMO_TASKS } from '@/lib/api/client';

export interface SearchResultItem {
  id: string;
  title: string;
  category: 'TRAIN' | 'WORK_ORDER' | 'TRACK' | 'STATION' | 'SIGNAL' | 'OHE' | 'CONFLICT' | 'GOVERNANCE';
  subtitle: string;
  targetUrl: string;
  code?: string;
  badge?: string;
  badgeColor?: 'blue' | 'green' | 'amber' | 'red';
}

const SEARCH_DATABASE: SearchResultItem[] = [
  // 1. Trains
  ...ACTIVE_TRAINS_GIS.map((t) => ({
    id: t.train_id,
    title: `${t.train_number} — ${t.name}`,
    category: 'TRAIN' as const,
    subtitle: `Current: km ${t.current_km.toFixed(1)} (${t.track}) • Speed: ${t.speed_kmh} km/h • Next: ${t.next_station}`,
    targetUrl: `/network?subtab=FLEET&trainId=${t.train_id}`,
    code: t.train_number,
    badge: t.status.replace(/_/g, ' '),
    badgeColor: t.status === 'ON_TIME' ? ('green' as const) : ('amber' as const),
  })),

  // 2. Work Orders
  ...DEMO_TASKS.map((task) => ({
    id: task.task_id,
    title: `${task.task_code || task.task_id}: ${task.title}`,
    category: 'WORK_ORDER' as const,
    subtitle: `Section: ${task.section_code || task.section_id} • Dept: ${task.department} • Req: ${(task.required_duration_minutes || 180) / 60}h`,
    targetUrl: `/work-orders?taskId=${task.task_id}`,
    code: task.task_code || task.task_id,
    badge: task.priority || 'ROUTINE',
    badgeColor: task.priority === 'CRITICAL' ? ('red' as const) : ('blue' as const),
  })),

  // 3. Track Sections
  ...CORRIDOR_SECTIONS_GIS.map((sec) => ({
    id: sec.code,
    title: `Section ${sec.code}: ${sec.name}`,
    category: 'TRACK' as const,
    subtitle: `${sec.from_station} → ${sec.to_station} (${sec.length_km} km) • Double Track (UP & DOWN Main) • ${sec.speed_limit_kmh} km/h`,
    targetUrl: `/planning?section=${sec.code}&subtab=MAP`,
    code: sec.code,
    badge: `${sec.speed_limit_kmh} KM/H`,
    badgeColor: 'blue' as const,
  })),

  // 4. Stations
  ...CORRIDOR_STATIONS_GIS.map((st) => ({
    id: st.code,
    title: `Station ${st.code} — ${st.name}`,
    category: 'STATION' as const,
    subtitle: `km ${st.distance_km.toFixed(1)} • ${st.track_count} Platform Lines • Division: ${st.division} (${st.facilities[0] || 'Interlocked'})`,
    targetUrl: `/network?subtab=STATIONS&station=${st.code}`,
    code: st.code,
    badge: 'INTERLOCKED',
    badgeColor: 'green' as const,
  })),

  // 5. Signals
  ...CORRIDOR_SIGNALS_GIS.map((sig) => ({
    id: sig.signal_id,
    title: `Signal ${sig.code}: ${sig.type.replace(/_/g, ' ')} (${sig.aspect})`,
    category: 'SIGNAL' as const,
    subtitle: `Location: km ${sig.km.toFixed(1)} on ${sig.track} Track • Auto Block System`,
    targetUrl: `/network?subtab=SIGNALS&signal=${sig.signal_id}`,
    code: sig.code,
    badge: sig.aspect,
    badgeColor: sig.aspect === 'PROCEED' ? ('green' as const) : sig.aspect === 'STOP' ? ('red' as const) : ('amber' as const),
  })),

  // 6. Catenary / OHE
  ...CORRIDOR_OHE_POSTS_GIS.map((ohe) => ({
    id: ohe.post_id,
    title: `OHE Mast ${ohe.code}: ${ohe.type.replace(/_/g, ' ')}`,
    category: 'OHE' as const,
    subtitle: `Location: km ${ohe.km.toFixed(1)} • Voltage: ${ohe.voltage_kv} kV AC Traction`,
    targetUrl: `/network?subtab=OHE&ohe=${ohe.post_id}`,
    code: ohe.code,
    badge: ohe.is_energized ? 'ENERGIZED' : 'ISOLATED',
    badgeColor: ohe.is_energized ? ('green' as const) : ('red' as const),
  })),

  // 7. Conflicts
  {
    id: 'CONF-HDW-01',
    title: 'Headway Buffer Violation: Express 12004 vs Freight 401',
    category: 'CONFLICT',
    subtitle: 'Section SEC-12 (Tundla – Etawah UP Mainline) • Safety Rule RULE-HEADWAY-01',
    targetUrl: '/planning?subtab=CONFLICTS&conflict=CONF-HDW-01',
    code: 'CONF-01',
    badge: 'CRITICAL',
    badgeColor: 'red',
  },

  // 8. Governance / Validation
  {
    id: 'VAL-STRUCT-01',
    title: 'VAL-STRUCT-01: Structural Topology & Boundary Adjacency',
    category: 'GOVERNANCE',
    subtitle: 'Statutory Safety Rule • 100% Pass Rate across 32 block sections',
    targetUrl: '/governance?rule=VAL-STRUCT-01',
    code: 'RULE-01',
    badge: 'PASSED',
    badgeColor: 'green',
  },
  {
    id: 'VAL-HEADWAY-05',
    title: 'VAL-HEADWAY-05: Train Separation & Signal Overlap Margins',
    category: 'GOVERNANCE',
    subtitle: 'Statutory Safety Rule • Verifies 7.0 min headway margin on express trunks',
    targetUrl: '/governance?rule=VAL-HEADWAY-05',
    code: 'RULE-05',
    badge: 'MANDATORY',
    badgeColor: 'amber',
  },
];

interface CommandSearchOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandSearchOverlay: React.FC<CommandSearchOverlayProps> = ({ isOpen, onClose }) => {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Handle keyboard shortcut Esc
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Filter items
  const filteredItems = useMemo(() => {
    if (!query.trim()) {
      return SEARCH_DATABASE.slice(0, 10);
    }
    const q = query.toLowerCase();
    return SEARCH_DATABASE.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q) ||
        item.code?.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
    ).slice(0, 16);
  }, [query]);

  // Key navigation (up/down/enter/escape)
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredItems.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredItems.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const selected = filteredItems[selectedIndex];
      if (selected) {
        handleSelectItem(selected);
      }
    }
  };

  const handleSelectItem = (item: SearchResultItem) => {
    onClose();
    router.push(item.targetUrl);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 select-none">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/70 backdrop-blur-xs transition-opacity"
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Corridor Command Search"
        className="relative z-50 w-full max-w-2xl bg-[#0B101C] border border-[#2D436D] rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans"
      >
        {/* Search Header */}
        <div className="flex items-center px-4 py-3.5 border-b border-[#1E2D4A] bg-[#0F172A] gap-3">
          <Search className="w-5 h-5 text-[#38BDF8] shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search trains, work orders, tracks, stations, signals, OHE, rules..."
            className="w-full bg-transparent text-[#F8FAFC] placeholder-[#64748B] text-sm focus:outline-hidden"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="text-[#64748B] hover:text-white p-1"
              aria-label="Clear search input"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onClose}
            aria-label="Close search"
            className="p-1 rounded text-[#94A3B8] hover:text-white hover:bg-[#1E2D4A] transition-colors"
          >
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-[#1E2D4A] text-[#94A3B8] rounded border border-[#334155] mr-1">
              ESC
            </kbd>
            <X className="w-4 h-4 inline-block sm:hidden" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-[60vh] overflow-y-auto divide-y divide-[#1E2D4A]/50 p-2">
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center text-[#64748B]">
              <Search className="w-8 h-8 mx-auto mb-2 text-[#1E2D4A]" />
              <p className="text-sm font-semibold text-[#94A3B8]">No matching railway entities</p>
              <p className="text-xs text-[#64748B] mt-1">Try searching by train number, section code, or task ID</p>
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const isSelected = index === selectedIndex;
              return (
                <div
                  key={`${item.category}-${item.id}`}
                  onClick={() => handleSelectItem(item)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`p-3 rounded-xl cursor-pointer flex items-center justify-between gap-3 transition-colors ${
                    isSelected
                      ? 'bg-[#141F36] border border-[#2563EB]/40 text-[#F8FAFC]'
                      : 'hover:bg-[#0F172A] text-[#CBD5E1]'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                        item.category === 'TRAIN'
                          ? 'bg-[#2563EB]/15 text-[#38BDF8] border-[#2563EB]/30'
                          : item.category === 'WORK_ORDER'
                          ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : item.category === 'TRACK'
                          ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30'
                          : item.category === 'STATION'
                          ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30'
                          : item.category === 'SIGNAL'
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : item.category === 'OHE'
                          ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                          : item.category === 'CONFLICT'
                          ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                          : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      }`}
                    >
                      {item.category === 'TRAIN' && <Train className="w-4 h-4" />}
                      {item.category === 'WORK_ORDER' && <Wrench className="w-4 h-4" />}
                      {item.category === 'TRACK' && <TrainTrack className="w-4 h-4" />}
                      {item.category === 'STATION' && <TrainTrack className="w-4 h-4" />}
                      {item.category === 'SIGNAL' && <Radio className="w-4 h-4" />}
                      {item.category === 'OHE' && <Zap className="w-4 h-4" />}
                      {item.category === 'CONFLICT' && <AlertTriangle className="w-4 h-4" />}
                      {item.category === 'GOVERNANCE' && <ShieldCheck className="w-4 h-4" />}
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-[#F8FAFC] truncate">
                          {item.title}
                        </span>
                        {item.badge && (
                          <span
                            className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold border ${
                              item.badgeColor === 'green'
                                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                                : item.badgeColor === 'red'
                                ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                                : item.badgeColor === 'amber'
                                ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                                : 'bg-[#2563EB]/15 text-[#93C5FD] border-[#2563EB]/30'
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-[#94A3B8] truncate mt-0.5">
                        {item.subtitle}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#0A0E17] text-[#64748B] border border-[#1E2D4A]">
                      {item.category.replace('_', ' ')}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-[#64748B]" />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2.5 bg-[#080C14] border-t border-[#1E2D4A] flex items-center justify-between text-[11px] text-[#64748B] font-mono">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <kbd className="px-1.5 py-0.5 rounded bg-[#1E2D4A] text-[#CBD5E1] text-[10px]">↑</kbd>
              <kbd className="px-1.5 py-0.5 rounded bg-[#1E2D4A] text-[#CBD5E1] text-[10px]">↓</kbd>
              <span>to navigate</span>
            </span>
            <span className="flex items-center gap-1.5">
              <kbd className="px-1.5 py-0.5 rounded bg-[#1E2D4A] text-[#CBD5E1] text-[10px]">↵</kbd>
              <span>to select</span>
            </span>
          </div>
          <span>TrackMeld Corridor Search</span>
        </div>
      </div>
    </div>
  );
};
