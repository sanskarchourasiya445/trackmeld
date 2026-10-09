'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { MapLibreRailwayMap } from '@/components/map/MapLibreRailwayMap';
import { EntityInspector, ContextualStation } from '@/components/planning/EntityInspector';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';
import { DigitalTwinInspectionModal } from '@/components/digital-twin/DigitalTwinInspectionModal';
import {
  CORRIDOR_STATIONS_GIS,
  CORRIDOR_SECTIONS_GIS,
  CORRIDOR_SIGNALS_GIS,
  CORRIDOR_OHE_POSTS_GIS,
  ACTIVE_TRAINS_GIS,
} from '@/lib/railway/corridorGisData';
import { DEMO_CORRIDOR } from '@/lib/api/client';
import { BlockSection } from '@/types/railway';
import {
  Network,
  GitBranch,
  MapPin,
  Radio,
  Zap,
  Train,
  ShieldCheck,
  Activity,
  Layers,
  Search,
  Filter,
  Eye,
  PanelRight,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NetworkPage() {
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-08');
  const [selectedStationCode, setSelectedStationCode] = useState<string | null>(null);
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);
  const [selectedOHEId, setSelectedOHEId] = useState<string | null>(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);
  const [isFullScreen, setIsFullScreen] = useState<boolean>(false);
  const [isDigitalTwinOpen, setIsDigitalTwinOpen] = useState<boolean>(false);
  const [digitalTwinSection, setDigitalTwinSection] = useState<string>('SEC-08');
  const [activeSubTab, setActiveSubTab] = useState<'MAP' | 'STATIONS' | 'TRACKS' | 'SIGNALS' | 'OHE' | 'FLEET'>('MAP');
  const [searchFilter, setSearchFilter] = useState('');

  // ESC to exit full screen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullScreen) {
        setIsFullScreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullScreen]);

  const selectedSection: BlockSection | null =
    DEMO_CORRIDOR.sections?.find((s) => s.code === selectedSectionCode || s.section_id === selectedSectionCode) || null;
  const selectedStation: ContextualStation | null =
    CORRIDOR_STATIONS_GIS.find((st) => st.code === selectedStationCode) || null;
  const selectedTrain =
    ACTIVE_TRAINS_GIS.find((t) => t.train_id === selectedTrainId) || null;
  const selectedSignal =
    CORRIDOR_SIGNALS_GIS.find((s) => s.signal_id === selectedSignalId || s.code === selectedSignalId) || null;
  const selectedOHE =
    CORRIDOR_OHE_POSTS_GIS.find((o) => o.post_id === selectedOHEId || o.code === selectedOHEId) || null;

  const handleOpenDigitalTwin = (secCode: string) => {
    setDigitalTwinSection(secCode);
    setIsDigitalTwinOpen(true);
  };

  const handleSelectAsset = (type: 'SECTION' | 'STATION' | 'TRAIN' | 'SIGNAL' | 'OHE', id: string) => {
    if (type === 'SECTION') {
      setSelectedSectionCode(id);
      setSelectedStationCode(null);
      setSelectedTrainId(null);
      setSelectedSignalId(null);
      setSelectedOHEId(null);
    } else if (type === 'STATION') {
      setSelectedStationCode(id);
      setSelectedSectionCode(null);
      setSelectedTrainId(null);
      setSelectedSignalId(null);
      setSelectedOHEId(null);
    } else if (type === 'TRAIN') {
      setSelectedTrainId(id);
      setSelectedSectionCode(null);
      setSelectedStationCode(null);
      setSelectedSignalId(null);
      setSelectedOHEId(null);
    } else if (type === 'SIGNAL') {
      setSelectedSignalId(id);
      setSelectedSectionCode(null);
      setSelectedStationCode(null);
      setSelectedTrainId(null);
      setSelectedOHEId(null);
    } else if (type === 'OHE') {
      setSelectedOHEId(id);
      setSelectedSectionCode(null);
      setSelectedStationCode(null);
      setSelectedTrainId(null);
      setSelectedSignalId(null);
    }
    setIsInspectorOpen(true);
  };

  const getActiveAssetTitle = () => {
    if (selectedStation) return `Station Hub: ${selectedStation.name} (${selectedStation.code})`;
    if (selectedSection) return `Track Section: ${selectedSection.name}`;
    if (selectedTrain) return `Train: ${selectedTrain.name} (${selectedTrain.train_number})`;
    if (selectedSignal) return `Signal: ${selectedSignal.code} (${selectedSignal.aspect})`;
    if (selectedOHE) return `OHE Post: ${selectedOHE.code} (${selectedOHE.voltage_kv} kV)`;
    return 'Asset Inspector';
  };

  return (
    <AppShell
      activeScenarioId="SCN-DEMO-001"
      scenarioName="Northern Trunk Corridor (NDLS - CNB)"
      planningHorizon="Infrastructure Assets: 440 km"
      tasksCount={30}
      trainsCount={50}
    >
      <div className="flex-1 flex flex-col h-full overflow-hidden p-5 sm:p-7 lg:p-8 gap-5 bg-[#04070D] font-sans max-w-[1900px] w-full mx-auto">
        {/* Network Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0B101C] border border-[#1E2D4A] rounded-xl px-6 py-4 shrink-0 shadow-lg">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#38BDF8]">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-[#F8FAFC]">Railway Network Infrastructure</h1>
                <p className="text-xs text-[#94A3B8] mt-0.5">
                  Physical corridor topology, interlocking stations, tracks, signals, and 25 kV AC traction OHE
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {activeSubTab === 'MAP' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsFullScreen((prev) => !prev)}
                className="border-[#2D436D] hover:bg-[#141F36] text-[#CBD5E1] hover:text-white text-xs font-semibold h-8.5 px-3"
                title={isFullScreen ? 'Exit Full Screen (Esc)' : 'Expand Map to Full Viewport'}
              >
                {isFullScreen ? <Minimize2 className="w-3.5 h-3.5 mr-1.5 text-[#38BDF8]" /> : <Maximize2 className="w-3.5 h-3.5 mr-1.5 text-[#38BDF8]" />}
                <span>{isFullScreen ? 'Exit Full Screen' : 'Expand Map'}</span>
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleOpenDigitalTwin(selectedSectionCode || 'SEC-08')}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#38BDF8] text-xs font-semibold h-8.5 px-3"
            >
              <Eye className="w-3.5 h-3.5 mr-1.5" />
              <span>Open 3D Twin</span>
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsInspectorOpen((prev) => !prev)}
              className={`border-[#2D436D] text-xs font-semibold h-8.5 px-3 transition-colors ${
                isInspectorOpen ? 'bg-[#141F36] text-white border-[#2563EB]' : 'text-[#CBD5E1] hover:text-white'
              }`}
            >
              <PanelRight className="w-3.5 h-3.5 mr-1.5 text-[#38BDF8]" />
              <span>{isInspectorOpen ? 'Close Drawer' : 'Inspect Asset'}</span>
            </Button>
          </div>
        </div>

        {/* Operational Statistics Row */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5 shrink-0">
          <div
            onClick={() => setActiveSubTab('STATIONS')}
            className={`bg-[#0B101C] border rounded-xl p-3.5 space-y-1 cursor-pointer transition-colors ${
              activeSubTab === 'STATIONS' ? 'border-[#38BDF8] bg-[#141F36]/60' : 'border-[#1E2D4A] hover:border-[#2D436D]'
            }`}
          >
            <span className="text-[10px] font-mono text-[#64748B] uppercase font-bold tracking-wider flex items-center gap-1">
              <MapPin className="w-3 h-3 text-[#38BDF8]" /> Stations
            </span>
            <div className="text-lg font-bold font-mono text-[#F8FAFC]">{CORRIDOR_STATIONS_GIS.length} Interlockings</div>
            <span className="text-[10.5px] text-[#94A3B8]">NDLS to CNB Hubs</span>
          </div>
          <div
            onClick={() => setActiveSubTab('TRACKS')}
            className={`bg-[#0B101C] border rounded-xl p-3.5 space-y-1 cursor-pointer transition-colors ${
              activeSubTab === 'TRACKS' ? 'border-[#38BDF8] bg-[#141F36]/60' : 'border-[#1E2D4A] hover:border-[#2D436D]'
            }`}
          >
            <span className="text-[10px] font-mono text-[#64748B] uppercase font-bold tracking-wider flex items-center gap-1">
              <GitBranch className="w-3 h-3 text-[#38BDF8]" /> Block Sections
            </span>
            <div className="text-lg font-bold font-mono text-[#F8FAFC]">{CORRIDOR_SECTIONS_GIS.length} Sections</div>
            <span className="text-[10.5px] text-[#94A3B8]">UIC 60 CWR 130 km/h</span>
          </div>
          <div
            onClick={() => setActiveSubTab('SIGNALS')}
            className={`bg-[#0B101C] border rounded-xl p-3.5 space-y-1 cursor-pointer transition-colors ${
              activeSubTab === 'SIGNALS' ? 'border-[#38BDF8] bg-[#141F36]/60' : 'border-[#1E2D4A] hover:border-[#2D436D]'
            }`}
          >
            <span className="text-[10px] font-mono text-[#64748B] uppercase font-bold tracking-wider flex items-center gap-1">
              <Radio className="w-3 h-3 text-[#38BDF8]" /> Signals
            </span>
            <div className="text-lg font-bold font-mono text-[#F8FAFC]">{CORRIDOR_SIGNALS_GIS.length} Signals</div>
            <span className="text-[10.5px] text-[#94A3B8]">Automatic Colour Light</span>
          </div>
          <div
            onClick={() => setActiveSubTab('OHE')}
            className={`bg-[#0B101C] border rounded-xl p-3.5 space-y-1 cursor-pointer transition-colors ${
              activeSubTab === 'OHE' ? 'border-[#38BDF8] bg-[#141F36]/60' : 'border-[#1E2D4A] hover:border-[#2D436D]'
            }`}
          >
            <span className="text-[10px] font-mono text-[#64748B] uppercase font-bold tracking-wider flex items-center gap-1">
              <Zap className="w-3 h-3 text-[#38BDF8]" /> Traction OHE
            </span>
            <div className="text-lg font-bold font-mono text-[#F8FAFC]">{CORRIDOR_OHE_POSTS_GIS.length} Mast Posts</div>
            <span className="text-[10.5px] text-[#94A3B8]">25 kV AC 50 Hz</span>
          </div>
          <div
            onClick={() => setActiveSubTab('FLEET')}
            className={`bg-[#0B101C] border rounded-xl p-3.5 space-y-1 cursor-pointer transition-colors ${
              activeSubTab === 'FLEET' ? 'border-[#38BDF8] bg-[#141F36]/60' : 'border-[#1E2D4A] hover:border-[#2D436D]'
            }`}
          >
            <span className="text-[10px] font-mono text-[#64748B] uppercase font-bold tracking-wider flex items-center gap-1">
              <Train className="w-3 h-3 text-[#38BDF8]" /> Active Fleet
            </span>
            <div className="text-lg font-bold font-mono text-[#F8FAFC]">{ACTIVE_TRAINS_GIS.length} Trains</div>
            <span className="text-[10.5px] text-emerald-400 font-semibold">100% Signal Monitored</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 bg-[#0B101C] border border-[#1E2D4A] rounded-xl p-1.5 overflow-x-auto shrink-0 text-xs">
          <button
            onClick={() => setActiveSubTab('MAP')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              activeSubTab === 'MAP'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Infrastructure Map</span>
          </button>
          <button
            onClick={() => setActiveSubTab('STATIONS')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              activeSubTab === 'STATIONS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <MapPin className="w-4 h-4" />
            <span>Stations ({CORRIDOR_STATIONS_GIS.length})</span>
          </button>
          <button
            onClick={() => setActiveSubTab('TRACKS')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              activeSubTab === 'TRACKS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <GitBranch className="w-4 h-4" />
            <span>Track Sections ({CORRIDOR_SECTIONS_GIS.length})</span>
          </button>
          <button
            onClick={() => setActiveSubTab('SIGNALS')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              activeSubTab === 'SIGNALS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Radio className="w-4 h-4" />
            <span>Signals ({CORRIDOR_SIGNALS_GIS.length})</span>
          </button>
          <button
            onClick={() => setActiveSubTab('OHE')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              activeSubTab === 'OHE'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Zap className="w-4 h-4" />
            <span>Catenary / OHE ({CORRIDOR_OHE_POSTS_GIS.length})</span>
          </button>
          <button
            onClick={() => setActiveSubTab('FLEET')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
              activeSubTab === 'FLEET'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Train className="w-4 h-4" />
            <span>Rolling Stock Fleet ({ACTIVE_TRAINS_GIS.length})</span>
          </button>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 min-h-0 overflow-hidden flex gap-3.5">
          <div className="flex-1 min-w-0 h-full overflow-hidden flex flex-col">
            {activeSubTab === 'MAP' && (
              <div className={isFullScreen ? "fixed inset-0 z-50 bg-[#070B14] p-4 sm:p-6 flex flex-col" : "flex-1 w-full h-full min-h-0 relative"}>
                {isFullScreen && (
                  <div className="flex items-center justify-between pb-3 mb-2 border-b border-[#1E2D4A] shrink-0">
                    <div className="flex items-center gap-2.5">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#2563EB]/20 text-[#38BDF8] border border-[#2563EB]/40">
                        FULL-SCREEN INFRASTRUCTURE MAP
                      </span>
                      <span className="text-sm font-bold text-[#F8FAFC]">Northern Trunk Corridor Topology (440 km)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setIsInspectorOpen((prev) => !prev)}
                        className={`border-[#2D436D] text-xs font-semibold h-8 px-3 ${
                          isInspectorOpen ? 'bg-[#141F36] text-white border-[#2563EB]' : 'text-[#CBD5E1] hover:text-white'
                        }`}
                      >
                        <PanelRight className="w-3.5 h-3.5 mr-1.5 text-[#38BDF8]" />
                        <span>Inspector</span>
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => setIsFullScreen(false)}
                        className="bg-[#141F36] hover:bg-[#1E2D4A] text-[#F8FAFC] border border-[#2D436D] text-xs font-semibold h-8 flex items-center gap-1.5"
                      >
                        <Minimize2 className="w-3.5 h-3.5 text-[#38BDF8]" />
                        <span>Exit Full Screen (ESC)</span>
                      </Button>
                    </div>
                  </div>
                )}
                <div className="flex-1 w-full h-full min-h-0 relative">
                  <MapLibreRailwayMap
                    selectedSectionCode={selectedSectionCode}
                    selectedTrainId={selectedTrainId}
                    onSelectSection={(code) => handleSelectAsset('SECTION', code)}
                    onSelectStation={(code) => handleSelectAsset('STATION', code)}
                    onSelectTrain={(id) => handleSelectAsset('TRAIN', id)}
                    onOpenDigitalTwin={handleOpenDigitalTwin}
                  />
                </div>
              </div>
            )}

            {/* TAB: STATIONS TABLE */}
            {activeSubTab === 'STATIONS' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden p-4 flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A] mb-3">
                  <span className="font-bold text-sm text-[#F8FAFC]">Major Interlocking Station Hubs</span>
                  <div className="text-xs text-[#64748B] font-mono">Northern Trunk Corridor</div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#0F172A] text-[#64748B] font-mono uppercase text-[10px] sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Code</th>
                        <th className="py-2.5 px-3">Station Name</th>
                        <th className="py-2.5 px-3">Chainage</th>
                        <th className="py-2.5 px-3">Tracks</th>
                        <th className="py-2.5 px-3">Division</th>
                        <th className="py-2.5 px-3">Key Facilities</th>
                        <th className="py-2.5 px-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1E2D4A]/50">
                      {CORRIDOR_STATIONS_GIS.map((st) => (
                        <tr
                          key={st.code}
                          onClick={() => {
                            setSelectedStationCode(st.code);
                            setSelectedSectionCode(null);
                            setIsInspectorOpen(true);
                          }}
                          className={`hover:bg-[#141F36] cursor-pointer transition-colors ${
                            selectedStationCode === st.code ? 'bg-[#141F36] border-l-2 border-[#38BDF8]' : ''
                          }`}
                        >
                          <td className="py-3 px-3 font-mono font-bold text-[#38BDF8]">{st.code}</td>
                          <td className="py-3 px-3 font-semibold text-[#F8FAFC]">{st.name}</td>
                          <td className="py-3 px-3 font-mono text-[#94A3B8]">km {st.distance_km}</td>
                          <td className="py-3 px-3 font-mono text-[#F8FAFC]">{st.track_count} Lines</td>
                          <td className="py-3 px-3 font-mono text-[#94A3B8]">{st.division}</td>
                          <td className="py-3 px-3">
                            <div className="flex flex-wrap gap-1">
                              {st.facilities.slice(0, 2).map((f, i) => (
                                <span key={i} className="text-[10px] bg-[#0A0E17] text-[#93C5FD] px-1.5 py-0.5 rounded border border-[#1E2D4A]">
                                  {f}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-3 px-3 text-right">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedStationCode(st.code);
                                setIsInspectorOpen(true);
                              }}
                              className="text-xs text-[#38BDF8] hover:text-white"
                            >
                              Inspect
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB: TRACK SECTIONS */}
            {activeSubTab === 'TRACKS' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden p-4 flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A] mb-3">
                  <span className="font-bold text-sm text-[#F8FAFC]">Block Sections & Running Tracks</span>
                  <div className="text-xs text-[#64748B] font-mono">Continuous Welded Rail (CWR) UIC 60</div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#0F172A] text-[#64748B] font-mono uppercase text-[10px] sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Section Code</th>
                        <th className="py-2.5 px-3">Name</th>
                        <th className="py-2.5 px-3">From → To</th>
                        <th className="py-2.5 px-3">Length</th>
                        <th className="py-2.5 px-3">Speed Limit</th>
                        <th className="py-2.5 px-3">UP Line Status</th>
                        <th className="py-2.5 px-3 text-right">3D Twin</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1E2D4A]/50">
                      {CORRIDOR_SECTIONS_GIS.map((sec) => (
                        <tr
                          key={sec.section_id}
                          onClick={() => {
                            setSelectedSectionCode(sec.code);
                            setSelectedStationCode(null);
                            setIsInspectorOpen(true);
                          }}
                          className={`hover:bg-[#141F36] cursor-pointer transition-colors ${
                            selectedSectionCode === sec.code ? 'bg-[#141F36] border-l-2 border-[#38BDF8]' : ''
                          }`}
                        >
                          <td className="py-3 px-3 font-mono font-bold text-[#38BDF8]">{sec.code}</td>
                          <td className="py-3 px-3 font-semibold text-[#F8FAFC]">{sec.name}</td>
                          <td className="py-3 px-3 font-mono text-[#94A3B8]">{sec.from_station} → {sec.to_station}</td>
                          <td className="py-3 px-3 font-mono text-[#F8FAFC]">{sec.length_km} km</td>
                          <td className="py-3 px-3 font-mono text-emerald-400 font-bold">{sec.speed_limit_kmh} km/h</td>
                          <td className="py-3 px-3">
                            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                              sec.up_line_status === 'POSSESSION'
                                ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                                : sec.up_line_status === 'CAUTION'
                                ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                                : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                            }`}>
                              {sec.up_line_status}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenDigitalTwin(sec.code);
                              }}
                              className="text-xs border-[#2D436D] text-[#38BDF8] hover:text-white"
                            >
                              Open 3D
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB: SIGNALS */}
            {activeSubTab === 'SIGNALS' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden p-4 flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A] mb-3">
                  <span className="font-bold text-sm text-[#F8FAFC]">Multi-Aspect Automatic Block Signals</span>
                  <div className="text-xs text-[#64748B] font-mono">Fail-Safe LED Color Light Signaling</div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#0F172A] text-[#64748B] font-mono uppercase text-[10px] sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Signal Code</th>
                        <th className="py-2.5 px-3">Type</th>
                        <th className="py-2.5 px-3">Chainage</th>
                        <th className="py-2.5 px-3">Track</th>
                        <th className="py-2.5 px-3">Aspect</th>
                        <th className="py-2.5 px-3 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1E2D4A]/50">
                      {CORRIDOR_SIGNALS_GIS.map((sig) => (
                        <tr
                          key={sig.signal_id}
                          onClick={() => {
                            setSelectedSignalId(sig.signal_id || sig.code);
                            setSelectedSectionCode(null);
                            setSelectedStationCode(null);
                            setSelectedTrainId(null);
                            setSelectedOHEId(null);
                            setIsInspectorOpen(true);
                          }}
                          className="hover:bg-[#141F36] cursor-pointer transition-colors"
                        >
                          <td className="py-3 px-3 font-mono font-bold text-[#38BDF8]">{sig.code}</td>
                          <td className="py-3 px-3 font-semibold text-[#F8FAFC]">{sig.type}</td>
                          <td className="py-3 px-3 font-mono text-[#94A3B8]">km {sig.km}</td>
                          <td className="py-3 px-3 font-mono text-[#F8FAFC]">{sig.track} MAIN</td>
                          <td className="py-3 px-3">
                            <span className={`inline-flex items-center gap-1.5 text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                              sig.aspect === 'PROCEED'
                                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                                : sig.aspect === 'CAUTION'
                                ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                                : 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                            }`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${
                                sig.aspect === 'PROCEED' ? 'bg-emerald-400' : sig.aspect === 'CAUTION' ? 'bg-amber-400' : 'bg-rose-400'
                              }`} />
                              {sig.aspect}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-[11px] text-[#64748B]">OPERATIONAL</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB: OHE */}
            {activeSubTab === 'OHE' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden p-4 flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A] mb-3">
                  <span className="font-bold text-sm text-[#F8FAFC]">25 kV AC 50 Hz Traction Electrification (OHE)</span>
                  <div className="text-xs text-[#64748B] font-mono">Traction Sub-Stations & Feeding Posts</div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#0F172A] text-[#64748B] font-mono uppercase text-[10px] sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Post ID</th>
                        <th className="py-2.5 px-3">Facility Type</th>
                        <th className="py-2.5 px-3">Chainage</th>
                        <th className="py-2.5 px-3">Voltage</th>
                        <th className="py-2.5 px-3">Power Status</th>
                        <th className="py-2.5 px-3 text-right">Permit (PTW)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1E2D4A]/50">
                      {CORRIDOR_OHE_POSTS_GIS.map((post) => (
                        <tr
                          key={post.post_id}
                          onClick={() => {
                            setSelectedOHEId(post.post_id || post.code);
                            setSelectedSectionCode(null);
                            setSelectedStationCode(null);
                            setSelectedTrainId(null);
                            setSelectedSignalId(null);
                            setIsInspectorOpen(true);
                          }}
                          className="hover:bg-[#141F36] cursor-pointer transition-colors"
                        >
                          <td className="py-3 px-3 font-mono font-bold text-[#38BDF8]">{post.code}</td>
                          <td className="py-3 px-3 font-semibold text-[#F8FAFC]">{post.type.replace('_', ' ')}</td>
                          <td className="py-3 px-3 font-mono text-[#94A3B8]">km {post.km}</td>
                          <td className="py-3 px-3 font-mono text-amber-400 font-bold">{post.voltage_kv} kV AC</td>
                          <td className="py-3 px-3">
                            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                              post.is_energized
                                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                                : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                            }`}>
                              {post.is_energized ? 'ENERGIZED' : 'DE-ENERGIZED (ISOLATED)'}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-[11px] text-[#64748B]">
                            {post.is_energized ? 'NORMAL' : 'PTW ACTIVE (TSK-0007)'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB: ROLLING STOCK FLEET */}
            {activeSubTab === 'FLEET' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden p-4 flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-[#1E2D4A] mb-3">
                  <span className="font-bold text-sm text-[#F8FAFC]">Active Rolling Stock Fleet Tracking</span>
                  <div className="text-xs text-[#64748B] font-mono">GPS-Telemetered Train Movements</div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#0F172A] text-[#64748B] font-mono uppercase text-[10px] sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Train Number</th>
                        <th className="py-2.5 px-3">Name</th>
                        <th className="py-2.5 px-3">Current Location</th>
                        <th className="py-2.5 px-3">Speed</th>
                        <th className="py-2.5 px-3">Assigned Track</th>
                        <th className="py-2.5 px-3">Schedule Status</th>
                        <th className="py-2.5 px-3 text-right">Next Station</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1E2D4A]/50">
                      {ACTIVE_TRAINS_GIS.map((train) => (
                        <tr
                          key={train.train_id}
                          onClick={() => {
                            setSelectedTrainId(train.train_id);
                            setSelectedSectionCode(null);
                            setSelectedStationCode(null);
                            setIsInspectorOpen(true);
                          }}
                          className={`hover:bg-[#141F36] cursor-pointer transition-colors ${
                            selectedTrainId === train.train_id ? 'bg-[#141F36] border-l-2 border-[#38BDF8]' : ''
                          }`}
                        >
                          <td className="py-3 px-3 font-mono font-bold text-[#38BDF8]">{train.train_number}</td>
                          <td className="py-3 px-3 font-semibold text-[#F8FAFC]">{train.name}</td>
                          <td className="py-3 px-3 font-mono text-[#94A3B8]">km {train.current_km}</td>
                          <td className="py-3 px-3 font-mono text-emerald-400 font-bold">{train.speed_kmh} km/h</td>
                          <td className="py-3 px-3 font-mono text-[#F8FAFC]">{train.track}</td>
                          <td className="py-3 px-3">
                            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                              train.status === 'ON_TIME'
                                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                                : train.status === 'HELD_AT_SIGNAL'
                                ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                                : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                            }`}>
                              {train.status.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right font-mono text-[11px] text-[#93C5FD]">
                            {train.next_station} ({train.eta_next})
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Slide-In Contextual Asset Detail Drawer (Rule 4 & 7) */}
      <ResponsiveDrawer
        isOpen={isInspectorOpen}
        onClose={() => setIsInspectorOpen(false)}
        title={getActiveAssetTitle()}
        subtitle="Northern Trunk Infrastructure Digital Twin Database"
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#2563EB]/20 text-[#38BDF8] font-bold border border-[#2563EB]/40">
            VERIFIED ASSET
          </span>
        }
        maxWidth="max-w-xl"
      >
        <div className="h-full">
          <EntityInspector
            selectedSection={selectedSection}
            selectedStation={selectedStation}
            selectedSignal={
              selectedSignal
                ? {
                    id: selectedSignal.signal_id || selectedSignal.code,
                    type: selectedSignal.type,
                    aspect: selectedSignal.aspect,
                    km: selectedSignal.km,
                    track: selectedSignal.track,
                    overlap_distance_m: 180,
                    interlocking: 'Electronic Interlocking (EI)',
                  }
                : null
            }
            selectedOHE={
              selectedOHE
                ? {
                    id: selectedOHE.code || selectedOHE.post_id,
                    km: selectedOHE.km,
                    track: 'UP & DOWN Main',
                    voltage_kv: selectedOHE.voltage_kv,
                    feeder_zone: selectedOHE.type.replace(/_/g, ' '),
                    contact_wire_height_m: 5.6,
                    neutral_section: false,
                  }
                : null
            }
            selectedTrain={
              selectedTrain
                ? {
                    train_id: selectedTrain.train_id,
                    train_number: selectedTrain.train_number,
                    train_name: selectedTrain.name,
                    direction: selectedTrain.direction,
                    priority_tier: 1,
                    track_id: selectedTrain.track,
                  }
                : null
            }
            isDrawer={true}
            hideHeader={true}
            onClose={() => setIsInspectorOpen(false)}
            onOpenDigitalTwin={handleOpenDigitalTwin}
          />
        </div>
      </ResponsiveDrawer>

      {/* 3D Digital Twin Modal */}
      <DigitalTwinInspectionModal
        isOpen={isDigitalTwinOpen}
        onClose={() => setIsDigitalTwinOpen(false)}
        sectionCode={digitalTwinSection}
        sectionName={
          CORRIDOR_SECTIONS_GIS.find(
            (s) => s.code === digitalTwinSection || s.section_id === digitalTwinSection
          )?.name || 'Northern Trunk Section'
        }
        kmRange="km 131.0 – 209.0"
        workOrderTitle="Section Track Geometry & Catenary Digital Twin"
      />
    </AppShell>
  );
}
