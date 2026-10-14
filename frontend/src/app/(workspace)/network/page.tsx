'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
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
  RefreshCw,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

type NetworkSubTab = 'MAP' | 'STATIONS' | 'TRACKS' | 'SIGNALS' | 'OHE' | 'FLEET';

const VALID_SUBTABS: NetworkSubTab[] = ['MAP', 'STATIONS', 'TRACKS', 'SIGNALS', 'OHE', 'FLEET'];

function NetworkPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Read initial subtab from URL query param (?subtab=STATIONS or ?tab=rolling-stock)
  const rawTab = searchParams.get('tab')?.toLowerCase();
  const rawSubtab = searchParams.get('subtab')?.toUpperCase() || (rawTab === 'rolling-stock' ? 'FLEET' : null);
  const initialSubtab: NetworkSubTab =
    rawSubtab && VALID_SUBTABS.includes(rawSubtab as NetworkSubTab)
      ? (rawSubtab as NetworkSubTab)
      : 'MAP';

  const [activeSubTab, setActiveSubTab] = useState<NetworkSubTab>(initialSubtab);
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-08');
  const [selectedStationCode, setSelectedStationCode] = useState<string | null>(null);
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);
  const [selectedOHEId, setSelectedOHEId] = useState<string | null>(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);
  const [isFullScreen, setIsFullScreen] = useState<boolean>(false);
  const [isDigitalTwinOpen, setIsDigitalTwinOpen] = useState<boolean>(false);
  const [digitalTwinSection, setDigitalTwinSection] = useState<string>('SEC-08');
  const [searchFilter, setSearchFilter] = useState('');

  // Bidirectional URL sync: synchronize state when searchParams changes (browser back/forward, deep link)
  useEffect(() => {
    const currentParam = searchParams.get('subtab')?.toUpperCase();
    if (currentParam && VALID_SUBTABS.includes(currentParam as NetworkSubTab)) {
      setActiveSubTab(currentParam as NetworkSubTab);
    } else if (!currentParam && activeSubTab !== 'MAP') {
      setActiveSubTab('MAP');
    }
  }, [searchParams]);

  // Handler for changing subtabs with pushState URL query updates
  const handleSubTabChange = (tab: NetworkSubTab) => {
    setActiveSubTab(tab);
    const params = new URLSearchParams(searchParams.toString());
    if (tab === 'MAP') {
      params.delete('subtab');
    } else {
      params.set('subtab', tab);
    }
    const queryString = params.toString() ? `?${params.toString()}` : '';
    router.push(`${pathname}${queryString}`);
  };

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

  // Domain search filters for table subviews
  const filteredStations = useMemo(() => {
    if (!searchFilter.trim()) return CORRIDOR_STATIONS_GIS;
    const q = searchFilter.toLowerCase();
    return CORRIDOR_STATIONS_GIS.filter(
      (s) =>
        s.code.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q) ||
        s.division.toLowerCase().includes(q) ||
        s.facilities.some((f) => f.toLowerCase().includes(q))
    );
  }, [searchFilter]);

  const filteredSections = useMemo(() => {
    if (!searchFilter.trim()) return CORRIDOR_SECTIONS_GIS;
    const q = searchFilter.toLowerCase();
    return CORRIDOR_SECTIONS_GIS.filter(
      (s) =>
        s.code.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q) ||
        s.from_station.toLowerCase().includes(q) ||
        s.to_station.toLowerCase().includes(q) ||
        s.up_line_status.toLowerCase().includes(q)
    );
  }, [searchFilter]);

  const filteredSignals = useMemo(() => {
    if (!searchFilter.trim()) return CORRIDOR_SIGNALS_GIS;
    const q = searchFilter.toLowerCase();
    return CORRIDOR_SIGNALS_GIS.filter(
      (s) =>
        s.code.toLowerCase().includes(q) ||
        s.type.toLowerCase().includes(q) ||
        s.aspect.toLowerCase().includes(q) ||
        s.track.toLowerCase().includes(q)
    );
  }, [searchFilter]);

  const filteredOHE = useMemo(() => {
    if (!searchFilter.trim()) return CORRIDOR_OHE_POSTS_GIS;
    const q = searchFilter.toLowerCase();
    return CORRIDOR_OHE_POSTS_GIS.filter(
      (o) =>
        o.code.toLowerCase().includes(q) ||
        o.type.toLowerCase().includes(q) ||
        String(o.voltage_kv).includes(q)
    );
  }, [searchFilter]);

  const filteredTrains = useMemo(() => {
    if (!searchFilter.trim()) return ACTIVE_TRAINS_GIS;
    const q = searchFilter.toLowerCase();
    return ACTIVE_TRAINS_GIS.filter(
      (t) =>
        t.train_number.toLowerCase().includes(q) ||
        t.name.toLowerCase().includes(q) ||
        t.status.toLowerCase().includes(q) ||
        t.next_station.toLowerCase().includes(q) ||
        t.destination.toLowerCase().includes(q)
    );
  }, [searchFilter]);

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
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden p-2 sm:p-2.5 lg:p-3 gap-2 bg-[#04070D] font-sans max-w-[1920px] w-full mx-auto">
        {/* Network Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 bg-[#0B101C] border border-[#1E2D4A] rounded-lg px-3.5 py-2 shrink-0 shadow-sm">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#38BDF8]">
                <Network className="w-4 h-4" />
              </div>
              <div>
                <h1 className="text-base font-bold text-[#F8FAFC]">Railway Network Infrastructure</h1>
                <p className="text-[11px] text-[#94A3B8]">
                  Physical corridor topology, interlocking stations, tracks, signals, and 25 kV AC traction OHE
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {activeSubTab === 'MAP' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsFullScreen((prev) => !prev)}
                className="border-[#2D436D] hover:bg-[#141F36] text-[#CBD5E1] hover:text-white text-xs font-semibold h-7.5 px-2.5"
                title={isFullScreen ? 'Exit Full Screen (Esc)' : 'Expand Map to Full Viewport'}
              >
                {isFullScreen ? <Minimize2 className="w-3.5 h-3.5 mr-1 text-[#38BDF8]" /> : <Maximize2 className="w-3.5 h-3.5 mr-1 text-[#38BDF8]" />}
                <span>{isFullScreen ? 'Exit Full' : 'Expand Map'}</span>
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleOpenDigitalTwin(selectedSectionCode || 'SEC-08')}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#38BDF8] text-xs font-semibold h-7.5 px-2.5"
            >
              <Eye className="w-3.5 h-3.5 mr-1" />
              <span>Open 3D Twin</span>
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsInspectorOpen((prev) => !prev)}
              className={`border-[#2D436D] text-xs font-semibold h-7.5 px-2.5 transition-colors ${
                isInspectorOpen ? 'bg-[#141F36] text-white border-[#2563EB]' : 'text-[#CBD5E1] hover:text-white'
              }`}
            >
              <PanelRight className="w-3.5 h-3.5 mr-1 text-[#38BDF8]" />
              <span>{isInspectorOpen ? 'Close Drawer' : 'Inspect Asset'}</span>
            </Button>
          </div>
        </div>

        {/* Consolidated Subtabs & Metric Bar */}
        <div className="flex items-center gap-1.5 bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-1 overflow-x-auto shrink-0 text-xs">
          <button
            onClick={() => handleSubTabChange('MAP')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeSubTab === 'MAP'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>Infrastructure Map</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${activeSubTab === 'MAP' ? 'bg-white/20 text-white' : 'bg-[#141F36] text-[#93C5FD]'}`}>
              440 km
            </span>
          </button>
          <button
            onClick={() => handleSubTabChange('STATIONS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeSubTab === 'STATIONS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <MapPin className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>Stations</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${activeSubTab === 'STATIONS' ? 'bg-white/20 text-white' : 'bg-[#141F36] text-[#93C5FD]'}`}>
              {CORRIDOR_STATIONS_GIS.length}
            </span>
          </button>
          <button
            onClick={() => handleSubTabChange('TRACKS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeSubTab === 'TRACKS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>Track Sections</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${activeSubTab === 'TRACKS' ? 'bg-white/20 text-white' : 'bg-[#141F36] text-[#93C5FD]'}`}>
              {CORRIDOR_SECTIONS_GIS.length}
            </span>
          </button>
          <button
            onClick={() => handleSubTabChange('SIGNALS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeSubTab === 'SIGNALS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Radio className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>Signals</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${activeSubTab === 'SIGNALS' ? 'bg-white/20 text-white' : 'bg-[#141F36] text-[#93C5FD]'}`}>
              {CORRIDOR_SIGNALS_GIS.length}
            </span>
          </button>
          <button
            onClick={() => handleSubTabChange('OHE')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeSubTab === 'OHE'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Zap className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>Catenary / OHE</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${activeSubTab === 'OHE' ? 'bg-white/20 text-white' : 'bg-[#141F36] text-[#93C5FD]'}`}>
              {CORRIDOR_OHE_POSTS_GIS.length}
            </span>
          </button>
          <button
            onClick={() => handleSubTabChange('FLEET')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-2 whitespace-nowrap ${
              activeSubTab === 'FLEET'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Train className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>Rolling Stock</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${activeSubTab === 'FLEET' ? 'bg-white/20 text-white' : 'bg-[#141F36] text-[#93C5FD]'}`}>
              {ACTIVE_TRAINS_GIS.length}
            </span>
          </button>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 min-h-0 overflow-hidden flex gap-2">
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
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-lg overflow-hidden p-2.5 sm:p-3 flex flex-col">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#1E2D4A] mb-2 gap-2">
                  <div>
                    <span className="font-bold text-sm text-[#F8FAFC]">Major Interlocking Station Hubs</span>
                    <div className="text-xs text-[#64748B] font-mono">Northern Trunk Corridor (NDLS – CNB)</div>
                  </div>
                  <div className="relative w-full sm:w-64">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                    <input
                      type="text"
                      placeholder="Filter stations..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="w-full bg-[#0F172A] border border-[#1E2D4A] rounded-lg pl-8 pr-7 py-1 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-[#2563EB] focus:outline-none"
                    />
                    {searchFilter && (
                      <button
                        onClick={() => setSearchFilter('')}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-[#F8FAFC]"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {filteredStations.length === 0 ? (
                    <div className="h-48 flex flex-col items-center justify-center text-[#64748B] text-xs">
                      <p>No stations match &ldquo;{searchFilter}&rdquo;</p>
                      <button onClick={() => setSearchFilter('')} className="mt-2 text-[#38BDF8] hover:underline font-mono">Reset Filter</button>
                    </div>
                  ) : (
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
                        {filteredStations.map((st) => (
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
                  )}
                </div>
              </div>
            )}

            {/* TAB: TRACK SECTIONS */}
            {activeSubTab === 'TRACKS' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-lg overflow-hidden p-2.5 sm:p-3 flex flex-col">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#1E2D4A] mb-2 gap-2">
                  <div>
                    <span className="font-bold text-sm text-[#F8FAFC]">Block Sections & Running Tracks</span>
                    <div className="text-xs text-[#64748B] font-mono">Continuous Welded Rail (CWR) UIC 60</div>
                  </div>
                  <div className="relative w-full sm:w-64">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                    <input
                      type="text"
                      placeholder="Filter sections..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="w-full bg-[#0F172A] border border-[#1E2D4A] rounded-lg pl-8 pr-7 py-1 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-[#2563EB] focus:outline-none"
                    />
                    {searchFilter && (
                      <button
                        onClick={() => setSearchFilter('')}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-[#F8FAFC]"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {filteredSections.length === 0 ? (
                    <div className="h-48 flex flex-col items-center justify-center text-[#64748B] text-xs">
                      <p>No track sections match &ldquo;{searchFilter}&rdquo;</p>
                      <button onClick={() => setSearchFilter('')} className="mt-2 text-[#38BDF8] hover:underline font-mono">Reset Filter</button>
                    </div>
                  ) : (
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
                        {filteredSections.map((sec) => (
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
                  )}
                </div>
              </div>
            )}

            {/* TAB: SIGNALS */}
            {activeSubTab === 'SIGNALS' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-lg overflow-hidden p-2.5 sm:p-3 flex flex-col">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#1E2D4A] mb-2 gap-2">
                  <div>
                    <span className="font-bold text-sm text-[#F8FAFC]">Multi-Aspect Automatic Block Signals</span>
                    <div className="text-xs text-[#64748B] font-mono">Fail-Safe LED Color Light Signaling</div>
                  </div>
                  <div className="relative w-full sm:w-64">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                    <input
                      type="text"
                      placeholder="Filter signals..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="w-full bg-[#0F172A] border border-[#1E2D4A] rounded-lg pl-8 pr-7 py-1 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-[#2563EB] focus:outline-none"
                    />
                    {searchFilter && (
                      <button
                        onClick={() => setSearchFilter('')}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-[#F8FAFC]"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {filteredSignals.length === 0 ? (
                    <div className="h-48 flex flex-col items-center justify-center text-[#64748B] text-xs">
                      <p>No signals match &ldquo;{searchFilter}&rdquo;</p>
                      <button onClick={() => setSearchFilter('')} className="mt-2 text-[#38BDF8] hover:underline font-mono">Reset Filter</button>
                    </div>
                  ) : (
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
                        {filteredSignals.map((sig) => (
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
                  )}
                </div>
              </div>
            )}

            {/* TAB: OHE */}
            {activeSubTab === 'OHE' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-lg overflow-hidden p-2.5 sm:p-3 flex flex-col">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#1E2D4A] mb-2 gap-2">
                  <div>
                    <span className="font-bold text-sm text-[#F8FAFC]">25 kV AC 50 Hz Traction Electrification (OHE)</span>
                    <div className="text-xs text-[#64748B] font-mono">Traction Sub-Stations & Feeding Posts</div>
                  </div>
                  <div className="relative w-full sm:w-64">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                    <input
                      type="text"
                      placeholder="Filter OHE posts..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="w-full bg-[#0F172A] border border-[#1E2D4A] rounded-lg pl-8 pr-7 py-1 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-[#2563EB] focus:outline-none"
                    />
                    {searchFilter && (
                      <button
                        onClick={() => setSearchFilter('')}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-[#F8FAFC]"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {filteredOHE.length === 0 ? (
                    <div className="h-48 flex flex-col items-center justify-center text-[#64748B] text-xs">
                      <p>No OHE posts match &ldquo;{searchFilter}&rdquo;</p>
                      <button onClick={() => setSearchFilter('')} className="mt-2 text-[#38BDF8] hover:underline font-mono">Reset Filter</button>
                    </div>
                  ) : (
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
                        {filteredOHE.map((post) => (
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
                  )}
                </div>
              </div>
            )}

            {/* TAB: ROLLING STOCK FLEET */}
            {activeSubTab === 'FLEET' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-lg overflow-hidden p-2.5 sm:p-3 flex flex-col">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#1E2D4A] mb-2 gap-2">
                  <div>
                    <span className="font-bold text-sm text-[#F8FAFC]">Active Rolling Stock Fleet Tracking</span>
                    <div className="text-xs text-[#64748B] font-mono">GPS-Telemetered Train Movements</div>
                  </div>
                  <div className="relative w-full sm:w-64">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                    <input
                      type="text"
                      placeholder="Filter fleet..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="w-full bg-[#0F172A] border border-[#1E2D4A] rounded-lg pl-8 pr-7 py-1 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-[#2563EB] focus:outline-none"
                    />
                    {searchFilter && (
                      <button
                        onClick={() => setSearchFilter('')}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-[#F8FAFC]"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {filteredTrains.length === 0 ? (
                    <div className="h-48 flex flex-col items-center justify-center text-[#64748B] text-xs">
                      <p>No trains match &ldquo;{searchFilter}&rdquo;</p>
                      <button onClick={() => setSearchFilter('')} className="mt-2 text-[#38BDF8] hover:underline font-mono">Reset Filter</button>
                    </div>
                  ) : (
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
                        {filteredTrains.map((train) => (
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
                  )}
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

export default function NetworkPage() {
  return (
    <React.Suspense
      fallback={
        <div className="flex h-screen w-full items-center justify-center bg-[#04070D] text-[#94A3B8]">
          <div className="flex items-center gap-2 font-mono text-sm">
            <RefreshCw className="w-4 h-4 animate-spin text-[#2563EB]" />
            <span>Loading TrackMeld Network Infrastructure...</span>
          </div>
        </div>
      }
    >
      <NetworkPageContent />
    </React.Suspense>
  );
}
