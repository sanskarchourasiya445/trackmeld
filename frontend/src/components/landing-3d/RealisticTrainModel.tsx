'use client';

import React, { useMemo } from 'react';
import * as THREE from 'three';

interface RealisticTrainModelProps {
  wheelRotation: number;
  isSelected?: boolean;
  showTelemetry?: boolean;
  lighting?: 'dawn' | 'night' | 'overcast';
}

/**
 * Authentic Indian Broad-Gauge 25 kV AC Electric Passenger Train
 * Context: Northern Railway / NCR Trunk Corridor (New Delhi – Kanpur Central / Tundla – Etawah Mainline)
 * Vehicle: High-Horsepower Broad-Gauge (1676 mm) Electric Locomotive + LHB Stainless-Steel Passenger Coaches
 *
 * Physical Specifications:
 * - Track Gauge: 1676 mm (Broad Gauge). Rail head height: Y = 0.44m.
 * - Wheel Diameter: 1092 mm (Radius: 0.546m). Wheel centers at Y = 0.986m, seated tangent to rails.
 * - Locomotive Body: Length ~20.5m, Width ~3.25m, Height ~4.2m from rail.
 * - Roof 25 kV AC Pantograph: Reaches Y = 5.38m contacting the OHE catenary contact wire.
 * - Authentic Dual Cab Fronts: Windshields with wipers, cowcatcher / cattle guard with CBC coupler.
 * - Dual-beam high-intensity sealed headlamps, red marker lamps, cyclops brow lamp.
 * - Cast steel Co-Co bogies with 3 axles each, primary springs, brake cylinders.
 * - Underframe central traction transformer, battery boxes, air tanks.
 * - Trailing LHB Coaches: Corrugated roof, tinted panoramic windows, interior illumination, FIAT bogies.
 */
export const RealisticTrainModel: React.FC<RealisticTrainModelProps> = ({
  wheelRotation,
  isSelected = false,
  showTelemetry = true,
  lighting = 'dawn',
}) => {
  const trackGauge = 1.676; // 1676 mm Broad Gauge
  const railTopY = 0.44;
  const wheelRadius = 0.546;
  const axleY = railTopY + wheelRadius; // 0.986m

  // ---------------------------------------------------------------------------
  // 1. PBR MATERIALS
  // ---------------------------------------------------------------------------
  const materials = useMemo(() => {
    // Locomotive Primary Body: Deep metallic navy / royal blue with refined specular response
    const locoNavy = new THREE.MeshStandardMaterial({
      color: '#0F2542',
      metalness: 0.55,
      roughness: 0.28,
    });

    // Locomotive Nose & Accent: Clean industrial platinum cream/white with silver fleck
    const locoCream = new THREE.MeshStandardMaterial({
      color: '#E2E8F0',
      metalness: 0.40,
      roughness: 0.32,
    });

    // Speed Stripe: TrackMeld Electric Blue (#2563EB)
    const speedStripe = new THREE.MeshStandardMaterial({
      color: '#2563EB',
      metalness: 0.60,
      roughness: 0.22,
    });

    // Red Front Warning Flash: Standard Indian Railways front warning chevron band
    const warningRed = new THREE.MeshStandardMaterial({
      color: '#DC2626',
      metalness: 0.30,
      roughness: 0.35,
    });

    // Lower Skirt & Cowcatcher: Tough dark graphite structural steel
    const underframeDark = new THREE.MeshStandardMaterial({
      color: '#0B0F17',
      metalness: 0.80,
      roughness: 0.45,
    });

    // Cast Steel Bogie Frames & Dampers
    const bogieSteel = new THREE.MeshStandardMaterial({
      color: '#1A2230',
      metalness: 0.75,
      roughness: 0.50,
    });

    // Machined Wheel Treads & Discs: Polished steel with metallic gleam
    const wheelSteel = new THREE.MeshStandardMaterial({
      color: '#CBD5E1',
      metalness: 0.95,
      roughness: 0.12,
    });

    // Laminated Cab Windshield Glass: Clear tinted with realistic reflectivity
    const windshieldGlass = new THREE.MeshStandardMaterial({
      color: '#38BDF8',
      metalness: 0.80,
      roughness: 0.08,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    });

    // LHB Coach Body: Stainless steel with horizontal swage lines
    const lhbStainless = new THREE.MeshStandardMaterial({
      color: '#CBD5E1',
      metalness: 0.85,
      roughness: 0.25,
    });

    // LHB Red/Maroon Waistline Band (Classic Rajdhani / Shatabdi Express livery)
    const lhbRedStripe = new THREE.MeshStandardMaterial({
      color: '#991B1B',
      metalness: 0.45,
      roughness: 0.30,
    });

    // LHB Roof: Ribbed grey stainless steel
    const lhbRoofGrey = new THREE.MeshStandardMaterial({
      color: '#64748B',
      metalness: 0.70,
      roughness: 0.40,
    });

    // Passenger Tinted Window Strip
    const coachWindows = new THREE.MeshStandardMaterial({
      color: '#070E1A',
      metalness: 0.90,
      roughness: 0.08,
      transparent: true,
      opacity: 0.90,
    });

    // Warm Interior Cabin Glow
    const interiorWarmGlow = new THREE.MeshBasicMaterial({
      color: '#FEF08A',
      transparent: true,
      opacity: lighting === 'night' ? 0.45 : 0.20,
    });

    // High-Intensity Projector Headlight Core
    const headlampBrilliant = new THREE.MeshBasicMaterial({
      color: '#FFFFFF',
    });

    // Headlamp Halo
    const headlampHalo = new THREE.MeshBasicMaterial({
      color: '#38BDF8',
      transparent: true,
      opacity: 0.75,
    });

    // Red Tail / Marker Lamp
    const markerRedLamp = new THREE.MeshBasicMaterial({
      color: '#EF4444',
    });

    // Amber LED Destination Display / Cab Indicator
    const destAmber = new THREE.MeshBasicMaterial({
      color: '#F59E0B',
    });

    // Console Dial Indicators (Emerald & Amber)
    const markerEmerald = new THREE.MeshBasicMaterial({
      color: '#10B981',
    });
    const markerAmber = new THREE.MeshBasicMaterial({
      color: '#F59E0B',
    });

    // Catenary Pantograph: High-tensile steel frame with graphite carbon collector
    const pantographArm = new THREE.MeshStandardMaterial({
      color: '#EF4444',
      metalness: 0.60,
      roughness: 0.35,
    });

    const pantoCarbonStrip = new THREE.MeshStandardMaterial({
      color: '#0F172A',
      metalness: 0.90,
      roughness: 0.20,
    });

    // Gangway Rubber Bellows
    const gangwayRubber = new THREE.MeshStandardMaterial({
      color: '#090D14',
      metalness: 0.10,
      roughness: 0.90,
    });

    // Telemetry Wireframe Accent
    const telemetryCyan = new THREE.LineBasicMaterial({
      color: isSelected ? '#38BDF8' : '#00F0FF',
      transparent: true,
      opacity: showTelemetry ? 0.25 : 0.0,
    });

    return {
      locoNavy,
      locoCream,
      speedStripe,
      warningRed,
      underframeDark,
      bogieSteel,
      wheelSteel,
      windshieldGlass,
      lhbStainless,
      lhbRedStripe,
      lhbRoofGrey,
      coachWindows,
      interiorWarmGlow,
      headlampBrilliant,
      headlampHalo,
      markerRedLamp,
      destAmber,
      markerEmerald,
      markerAmber,
      pantographArm,
      pantoCarbonStrip,
      gangwayRubber,
      telemetryCyan,
    };
  }, [isSelected, showTelemetry, lighting]);

  // ---------------------------------------------------------------------------
  // 2. HELPER: BOGIE WITH ROTATING BROAD-GAUGE WHEELSETS
  // ---------------------------------------------------------------------------
  const renderBogie = (key: string, xPos: number, axleCount: 2 | 3 = 3) => {
    const axleSpacing = 1.75; // meters between axles in Co-Co bogie
    const axleOffsets =
      axleCount === 3 ? [-axleSpacing, 0, axleSpacing] : [-axleSpacing / 2, axleSpacing / 2];
    const halfGauge = trackGauge / 2; // 0.838m

    return (
      <group key={key} position={[xPos, 0, 0]}>
        {/* Bogie Cast Steel Frame Bolster */}
        <mesh position={[0, axleY + 0.28, 0]} material={materials.bogieSteel} castShadow receiveShadow>
          <boxGeometry args={[axleCount === 3 ? 4.8 : 3.2, 0.24, 2.35]} />
        </mesh>

        {/* Bogie Side Frames (Left & Right) */}
        <mesh position={[0, axleY + 0.12, -halfGauge - 0.24]} material={materials.bogieSteel} castShadow>
          <boxGeometry args={[axleCount === 3 ? 4.6 : 3.0, 0.38, 0.18]} />
        </mesh>
        <mesh position={[0, axleY + 0.12, halfGauge + 0.24]} material={materials.bogieSteel} castShadow>
          <boxGeometry args={[axleCount === 3 ? 4.6 : 3.0, 0.38, 0.18]} />
        </mesh>

        {/* Primary Helical Coil Suspension Springs above each axle box */}
        {axleOffsets.map((axleX, idx) => (
          <group key={`susp-${idx}`} position={[axleX, axleY + 0.22, 0]}>
            <mesh position={[0, 0, -halfGauge - 0.24]} material={materials.underframeDark}>
              <cylinderGeometry args={[0.10, 0.10, 0.28, 12]} />
            </mesh>
            <mesh position={[0, 0, halfGauge + 0.24]} material={materials.underframeDark}>
              <cylinderGeometry args={[0.10, 0.10, 0.28, 12]} />
            </mesh>
          </group>
        ))}

        {/* Wheelsets (Axle + Left Flanged Wheel + Right Flanged Wheel) */}
        {axleOffsets.map((axleX, idx) => (
          <group key={`wheelset-${idx}`} position={[axleX, axleY, 0]}>
            {/* Rotating Wheelset Group */}
            <group rotation={[0, 0, wheelRotation]}>
              {/* Solid Steel Axle */}
              <mesh rotation={[Math.PI / 2, 0, 0]} material={materials.underframeDark}>
                <cylinderGeometry args={[0.09, 0.09, trackGauge + 0.2, 16]} />
              </mesh>

              {/* Left Wheel (Tread + Flange) */}
              <group position={[0, 0, -halfGauge]}>
                {/* Wheel Tread (seated exactly tangent to rail top) */}
                <mesh rotation={[Math.PI / 2, 0, 0]} material={materials.wheelSteel}>
                  <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
                </mesh>
                {/* Wheel Flange (inner lip) */}
                <mesh position={[0, 0, 0.06]} rotation={[Math.PI / 2, 0, 0]} material={materials.bogieSteel}>
                  <cylinderGeometry args={[wheelRadius + 0.035, wheelRadius + 0.035, 0.035, 24]} />
                </mesh>
                {/* Ventilated Brake Disc Hub */}
                <mesh position={[0, 0, -0.05]} rotation={[Math.PI / 2, 0, 0]} material={materials.bogieSteel}>
                  <cylinderGeometry args={[wheelRadius * 0.58, wheelRadius * 0.58, 0.04, 16]} />
                </mesh>
              </group>

              {/* Right Wheel (Tread + Flange) */}
              <group position={[0, 0, halfGauge]}>
                <mesh rotation={[Math.PI / 2, 0, 0]} material={materials.wheelSteel}>
                  <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
                </mesh>
                <mesh position={[0, 0, -0.06]} rotation={[Math.PI / 2, 0, 0]} material={materials.bogieSteel}>
                  <cylinderGeometry args={[wheelRadius + 0.035, wheelRadius + 0.035, 0.035, 24]} />
                </mesh>
                <mesh position={[0, 0, 0.05]} rotation={[Math.PI / 2, 0, 0]} material={materials.bogieSteel}>
                  <cylinderGeometry args={[wheelRadius * 0.58, wheelRadius * 0.58, 0.04, 16]} />
                </mesh>
              </group>
            </group>
          </group>
        ))}
      </group>
    );
  };

  // ---------------------------------------------------------------------------
  // 3. HELPER: 25 kV AC HIGH-VOLTAGE ROOF PANTOGRAPH
  // ---------------------------------------------------------------------------
  const renderPantograph = (xPos: number, isRaised: boolean = true) => {
    const roofY = 4.22;
    const catenaryContactY = 5.38; // Contact wire height
    const pantoHeight = isRaised ? catenaryContactY - roofY : 0.35;

    return (
      <group position={[xPos, roofY, 0]}>
        {/* Base Frame & Insulator Mounts */}
        <mesh position={[0, 0.05, 0]} material={materials.underframeDark}>
          <boxGeometry args={[2.2, 0.08, 1.4]} />
        </mesh>
        {/* 4 Porcelain Stand-off Insulators */}
        {[-0.8, 0.8].map((ox) =>
          [-0.5, 0.5].map((oz) => (
            <mesh key={`panto-ins-${ox}-${oz}`} position={[ox, 0.14, oz]} material={materials.warningRed}>
              <cylinderGeometry args={[0.08, 0.08, 0.22, 10]} />
            </mesh>
          ))
        )}

        {isRaised && (
          <>
            {/* Lower Articulated Arm (Angle up-backward) */}
            <group position={[-0.7, 0.24, 0]} rotation={[0, 0, 0.55]}>
              <mesh position={[0.7, 0, 0]} material={materials.pantographArm}>
                <boxGeometry args={[1.5, 0.06, 0.08]} />
              </mesh>

              {/* Upper Articulated Arm (Angle forward to contact wire) */}
              <group position={[1.4, 0, 0]} rotation={[0, 0, -1.05]}>
                <mesh position={[0.75, 0, 0]} material={materials.pantographArm}>
                  <boxGeometry args={[1.6, 0.05, 0.06]} />
                </mesh>

                {/* Pantograph Head & Carbon Contact Collector Pan */}
                <group position={[1.5, 0, 0]} rotation={[0, 0, 0.5]}>
                  {/* Collector Bow Horns */}
                  <mesh position={[0, 0.02, 0]} material={materials.pantoCarbonStrip}>
                    <boxGeometry args={[0.24, 0.04, 2.0]} />
                  </mesh>
                  {/* Carbon Wear Strip Contact Plate (Contacts wire exactly at Y = 5.38m) */}
                  <mesh position={[0, 0.045, 0]} material={materials.wheelSteel}>
                    <boxGeometry args={[0.18, 0.015, 1.6]} />
                  </mesh>
                </group>
              </group>
            </group>
          </>
        )}
      </group>
    );
  };

  // ---------------------------------------------------------------------------
  // 4. MAIN WAP-7 CLASS HIGH-SPEED ELECTRIC LOCOMOTIVE
  // Center at X = 0, Length = 20.5m, Width = 3.25m, Height = 4.2m
  // ---------------------------------------------------------------------------
  return (
    <group position={[0, 0, -2.0]}>
      {/* ==================================================================== */}
      {/* LOCOMOTIVE ASSEMBLY                                                  */}
      {/* ==================================================================== */}
      <group position={[0, 0, 0]}>
        {/* Main Bodyshell (Steel Boxcab Structure) */}
        {/* Lower Main Hull */}
        <mesh position={[0, 2.45, 0]} material={materials.locoNavy} castShadow receiveShadow>
          <boxGeometry args={[18.8, 2.30, 3.18]} />
        </mesh>

        {/* Waistline Cobalt Speed Stripe */}
        <mesh position={[0, 2.05, 0]} material={materials.speedStripe}>
          <boxGeometry args={[18.82, 0.36, 3.20]} />
        </mesh>

        {/* Upper Cantrail / Roof Crown (Curved Arched Roof) */}
        <group position={[0, 3.60, 0]} scale={[1, 0.28, 1]}>
          <mesh rotation={[0, 0, Math.PI / 2]} material={materials.locoNavy} castShadow>
            <cylinderGeometry args={[1.59, 1.59, 18.8, 16, 1, false, 0, Math.PI]} />
          </mesh>
        </group>

        {/* Dynamic Brake Resistor Louver Banks along roof */}
        {[-4.5, -1.5, 1.5, 4.5].map((lx) => (
          <mesh key={`louver-${lx}`} position={[lx, 4.18, 0]} material={materials.underframeDark}>
            <boxGeometry args={[2.2, 0.18, 1.8]} />
          </mesh>
        ))}

        {/* Heavy Underframe Chassis Girder */}
        <mesh position={[0, 1.25, 0]} material={materials.underframeDark} castShadow receiveShadow>
          <boxGeometry args={[19.6, 0.32, 3.10]} />
        </mesh>

        {/* Central Underslung Traction Transformer & Battery Enclosures */}
        <mesh position={[0, 0.85, 0]} material={materials.underframeDark} castShadow>
          <boxGeometry args={[5.8, 0.68, 2.60]} />
        </mesh>
        {/* Auxiliary Air Reservoirs (Twin cylinders under chassis) */}
        <mesh position={[0, 0.82, -1.05]} rotation={[0, 0, Math.PI / 2]} material={materials.bogieSteel}>
          <cylinderGeometry args={[0.28, 0.28, 4.2, 16]} />
        </mesh>
        <mesh position={[0, 0.82, 1.05]} rotation={[0, 0, Math.PI / 2]} material={materials.bogieSteel}>
          <cylinderGeometry args={[0.28, 0.28, 4.2, 16]} />
        </mesh>

        {/* ------------------------------------------------------------------ */}
        {/* FRONT CAB (NOSE AT X = +9.4m, FACING FORWARD)                     */}
        {/* ------------------------------------------------------------------ */}
        <group position={[9.4, 0, 0]}>
          {/* Lower Aerodynamic Nose Hood (height 1.2m, Y = 1.3 to 2.5) */}
          <mesh position={[0.75, 1.90, 0]} material={materials.locoNavy} castShadow>
            <boxGeometry args={[1.5, 1.20, 3.12]} />
          </mesh>

          {/* Front Warning Chevrons / Contrast Face Band on Hood */}
          <mesh position={[1.48, 1.90, 0]} material={materials.locoCream}>
            <boxGeometry args={[0.08, 1.10, 3.05]} />
          </mesh>
          <mesh position={[1.50, 1.70, 0]} material={materials.warningRed}>
            <boxGeometry args={[0.08, 0.32, 2.95]} />
          </mesh>

          {/* Cab Fascia Below Windshield (Y = 2.45 to 2.65) */}
          <mesh position={[0.95, 2.55, 0]} material={materials.locoNavy}>
            <boxGeometry args={[1.1, 0.20, 3.12]} />
          </mesh>

          {/* Cab Sun-Visor / Brow Cap Above Windshield (Y = 3.45 to 3.65) */}
          <mesh position={[0.95, 3.55, 0]} material={materials.locoNavy}>
            <boxGeometry args={[1.1, 0.20, 3.12]} />
          </mesh>

          {/* Left Cab Side Pillar */}
          <mesh position={[0.95, 3.05, -1.48]} material={materials.locoNavy}>
            <boxGeometry args={[1.1, 0.80, 0.16]} />
          </mesh>
          {/* Right Cab Side Pillar */}
          <mesh position={[0.95, 3.05, 1.48]} material={materials.locoNavy}>
            <boxGeometry args={[1.1, 0.80, 0.16]} />
          </mesh>

          {/* Raked Cab Windshields (Dual Glazed Panes: Left & Right) */}
          <group position={[1.15, 3.05, 0]}>
            {/* Left Driver Windshield */}
            <mesh position={[0, 0, -0.75]} rotation={[0, 0, -0.22]} material={materials.windshieldGlass}>
              <boxGeometry args={[0.04, 0.80, 1.20]} />
            </mesh>
            {/* Right Assistant Windshield */}
            <mesh position={[0, 0, 0.75]} rotation={[0, 0, -0.22]} material={materials.windshieldGlass}>
              <boxGeometry args={[0.04, 0.80, 1.20]} />
            </mesh>
            {/* Center Windscreen Mullion Pillar */}
            <mesh position={[0.02, 0, 0]} rotation={[0, 0, -0.22]} material={materials.underframeDark}>
              <boxGeometry args={[0.08, 0.84, 0.20]} />
            </mesh>
          </group>

          {/* Driver Cab Console Desk & Illuminated Telemetry Displays */}
          <group position={[0.45, 2.40, 0]}>
            <mesh material={materials.underframeDark}>
              <boxGeometry args={[0.85, 0.35, 2.90]} />
            </mesh>
            {/* Driver Speedometer Dial (Cyan) */}
            <mesh position={[0.20, 0.20, -0.75]} rotation={[-0.45, 0, 0]} material={materials.markerEmerald}>
              <boxGeometry args={[0.25, 0.12, 0.35]} />
            </mesh>
            {/* Assistant Display (Amber) */}
            <mesh position={[0.20, 0.20, 0.75]} rotation={[-0.45, 0, 0]} material={materials.markerAmber}>
              <boxGeometry args={[0.25, 0.12, 0.35]} />
            </mesh>
          </group>

          {/* Cab Side Windows */}
          <mesh position={[-0.45, 3.05, -1.56]} material={materials.windshieldGlass}>
            <boxGeometry args={[1.1, 0.65, 0.05]} />
          </mesh>
          <mesh position={[-0.45, 3.05, 1.56]} material={materials.windshieldGlass}>
            <boxGeometry args={[1.1, 0.65, 0.05]} />
          </mesh>

          {/* Front Sealed-Beam Projector Headlights (Dual Twin Beams) */}
          {/* Left Headlamp Cluster */}
          <group position={[1.52, 1.62, -0.92]}>
            <mesh material={materials.underframeDark}>
              <boxGeometry args={[0.12, 0.26, 0.52]} />
            </mesh>
            <mesh position={[0.07, 0, -0.12]} material={materials.headlampBrilliant}>
              <circleGeometry args={[0.09, 16]} />
            </mesh>
            <mesh position={[0.07, 0, 0.12]} material={materials.headlampBrilliant}>
              <circleGeometry args={[0.09, 16]} />
            </mesh>
            {/* Red Tail Marker Lamp */}
            <mesh position={[0.07, 0.16, 0]} material={materials.markerRedLamp}>
              <circleGeometry args={[0.045, 12]} />
            </mesh>
          </group>

          {/* Right Headlamp Cluster */}
          <group position={[1.52, 1.62, 0.92]}>
            <mesh material={materials.underframeDark}>
              <boxGeometry args={[0.12, 0.26, 0.52]} />
            </mesh>
            <mesh position={[0.07, 0, -0.12]} material={materials.headlampBrilliant}>
              <circleGeometry args={[0.09, 16]} />
            </mesh>
            <mesh position={[0.07, 0, 0.12]} material={materials.headlampBrilliant}>
              <circleGeometry args={[0.09, 16]} />
            </mesh>
            <mesh position={[0.07, 0.16, 0]} material={materials.markerRedLamp}>
              <circleGeometry args={[0.045, 12]} />
            </mesh>
          </group>

          {/* Upper Cyclops High-Beam Projector (Center of Cab Brow) */}
          <group position={[0.82, 3.82, 0]}>
            <mesh material={materials.underframeDark}>
              <boxGeometry args={[0.22, 0.24, 0.28]} />
            </mesh>
            <mesh position={[0.12, 0, 0]} rotation={[0, Math.PI / 2, 0]} material={materials.headlampBrilliant}>
              <circleGeometry args={[0.10, 16]} />
            </mesh>
          </group>

          {/* Forward Track Illuminating Powerful Spotlights */}
          <spotLight
            position={[1.8, 1.62, 0]}
            target-position={[60, 0.44, 0]}
            color="#FFFBEB"
            intensity={lighting === 'night' ? 24.0 : 14.0}
            distance={95}
            angle={Math.PI / 5.5}
            penumbra={0.55}
            castShadow
          />

          {/* Heavy Steel Cowcatcher / Cattle Guard (V-shaped plow) */}
          <group position={[1.20, 0.68, 0]}>
            <mesh rotation={[0, 0, -0.35]} material={materials.underframeDark}>
              <boxGeometry args={[0.62, 0.44, 2.75]} />
            </mesh>
            {/* Center Buffer Coupler (CBC Knuckle Head) */}
            <mesh position={[0.42, 0.12, 0]} material={materials.bogieSteel}>
              <boxGeometry args={[0.45, 0.28, 0.32]} />
            </mesh>
          </group>
        </group>

        {/* ------------------------------------------------------------------ */}
        {/* REAR CAB (AT X = -9.4m)                                            */}
        {/* ------------------------------------------------------------------ */}
        <group position={[-9.4, 0, 0]} rotation={[0, Math.PI, 0]}>
          <mesh position={[0.75, 2.30, 0]} material={materials.locoNavy} castShadow>
            <boxGeometry args={[1.5, 2.0, 3.12]} />
          </mesh>
          <mesh position={[1.48, 2.10, 0]} material={materials.locoCream}>
            <boxGeometry args={[0.08, 1.30, 3.05]} />
          </mesh>
          {/* Rear Coupler */}
          <mesh position={[1.45, 0.80, 0]} material={materials.bogieSteel}>
            <boxGeometry args={[0.45, 0.28, 0.32]} />
          </mesh>
        </group>

        {/* ------------------------------------------------------------------ */}
        {/* ROOF EQUIPMENT & DUAL PANTOGRAPHS                                 */}
        {/* ------------------------------------------------------------------ */}
        {/* Rear Pantograph Raised (Active current collector at X = -5.8m) */}
        {renderPantograph(-5.8, true)}
        {/* Front Pantograph Lowered (Reserve at X = +5.8m) */}
        {renderPantograph(5.8, false)}

        {/* High-Voltage Roof Busbar Cable */}
        <mesh position={[0, 4.38, 0.65]} material={materials.warningRed}>
          <boxGeometry args={[14.5, 0.04, 0.04]} />
        </mesh>

        {/* ------------------------------------------------------------------ */}
        {/* LOCOMOTIVE CO-CO BOGIES (3 AXLES EACH)                             */}
        {/* ------------------------------------------------------------------ */}
        {renderBogie('loco-bogie-front', 5.6, 3)}
        {renderBogie('loco-bogie-rear', -5.6, 3)}
      </group>

      {/* ==================================================================== */}
      {/* LHB PASSENGER COACH 1 (EXPRESS CHAIR CAR / EXECUTIVE LHB)             */}
      {/* Center at X = -22.5m, Length = 21.0m                                 */}
      {/* ==================================================================== */}
      <group position={[-22.5, 0, 0]}>
        {/* Gangway Rubber Vestibule Bellows to Locomotive */}
        <mesh position={[11.0, 2.35, 0]} material={materials.gangwayRubber}>
          <boxGeometry args={[1.0, 2.45, 1.65]} />
        </mesh>

        {/* Stainless Steel Coach Bodyshell */}
        <mesh position={[0, 2.45, 0]} material={materials.lhbStainless} castShadow receiveShadow>
          <boxGeometry args={[20.5, 2.35, 3.20]} />
        </mesh>

        {/* Maroon / Red Waistline Speed Band */}
        <mesh position={[0, 2.15, 0]} material={materials.lhbRedStripe}>
          <boxGeometry args={[20.52, 0.45, 3.22]} />
        </mesh>

        {/* Ribbed Stainless Steel Arched Roof */}
        <group position={[0, 3.62, 0]} scale={[1, 0.28, 1]}>
          <mesh rotation={[0, 0, Math.PI / 2]} material={materials.lhbRoofGrey} castShadow>
            <cylinderGeometry args={[1.60, 1.60, 20.5, 16, 1, false, 0, Math.PI]} />
          </mesh>
        </group>

        {/* Panoramic Passenger Windows (Continuous Glazed Band) */}
        <mesh position={[0, 2.55, 0]} material={materials.coachWindows}>
          <boxGeometry args={[18.2, 0.62, 3.24]} />
        </mesh>

        {/* Interior Cabin Illumination */}
        <mesh position={[0, 2.55, 0]} material={materials.interiorWarmGlow}>
          <boxGeometry args={[18.0, 0.58, 3.0]} />
        </mesh>

        {/* Passenger Entrance Doors (4 corner doors) */}
        {[-9.2, 9.2].map((dx) => (
          <group key={`door-${dx}`}>
            <mesh position={[dx, 2.25, -1.61]} material={materials.underframeDark}>
              <boxGeometry args={[0.95, 1.85, 0.04]} />
            </mesh>
            <mesh position={[dx, 2.25, 1.61]} material={materials.underframeDark}>
              <boxGeometry args={[0.95, 1.85, 0.04]} />
            </mesh>
          </group>
        ))}

        {/* Underframe Skirting & AC Equipment Boxes */}
        <mesh position={[0, 1.15, 0]} material={materials.underframeDark}>
          <boxGeometry args={[14.2, 0.55, 2.55]} />
        </mesh>

        {/* FIAT 2-Axle High-Speed Bogies */}
        {renderBogie('lhb1-bogie-f', 7.2, 2)}
        {renderBogie('lhb1-bogie-r', -7.2, 2)}
      </group>

      {/* ==================================================================== */}
      {/* LHB PASSENGER COACH 2 (RECEDING INTO PERSPECTIVE DISTANCE)           */}
      {/* Center at X = -44.5m, Length = 21.0m                                 */}
      {/* ==================================================================== */}
      <group position={[-44.5, 0, 0]}>
        {/* Inter-coach Gangway Vestibule */}
        <mesh position={[11.0, 2.35, 0]} material={materials.gangwayRubber}>
          <boxGeometry args={[1.0, 2.45, 1.65]} />
        </mesh>

        <mesh position={[0, 2.45, 0]} material={materials.lhbStainless} castShadow receiveShadow>
          <boxGeometry args={[20.5, 2.35, 3.20]} />
        </mesh>

        <mesh position={[0, 2.15, 0]} material={materials.lhbRedStripe}>
          <boxGeometry args={[20.52, 0.45, 3.22]} />
        </mesh>

        {/* Ribbed Stainless Steel Arched Roof */}
        <group position={[0, 3.62, 0]} scale={[1, 0.28, 1]}>
          <mesh rotation={[0, 0, Math.PI / 2]} material={materials.lhbRoofGrey} castShadow>
            <cylinderGeometry args={[1.60, 1.60, 20.5, 16, 1, false, 0, Math.PI]} />
          </mesh>
        </group>

        <mesh position={[0, 2.55, 0]} material={materials.coachWindows}>
          <boxGeometry args={[18.2, 0.62, 3.24]} />
        </mesh>

        <mesh position={[0, 2.55, 0]} material={materials.interiorWarmGlow}>
          <boxGeometry args={[18.0, 0.58, 3.0]} />
        </mesh>

        <mesh position={[0, 1.15, 0]} material={materials.underframeDark}>
          <boxGeometry args={[14.2, 0.55, 2.55]} />
        </mesh>

        {renderBogie('lhb2-bogie-f', 7.2, 2)}
        {renderBogie('lhb2-bogie-r', -7.2, 2)}
      </group>
    </group>
  );
};
