'use client';

import * as THREE from 'three';

let cachedCoachTexture: THREE.CanvasTexture | null = null;
let cachedNoseTexture: THREE.CanvasTexture | null = null;

/**
 * Procedural Canvas Texture for Streamlined Passenger Coach Fuselage:
 * - Anti-aliased Platinum Silver automotive bodyshell (#ECEFF1)
 * - Continuous Indian Railways Signal Orange roofline accent band (#EA580C)
 * - Dark tinted panoramic passenger window band with silver mullions & warm interior reflection
 * - Flush passenger plug doors with rubber seals and door access indicators
 * - Dark anthracite lower aerodynamic underbody skirt with orange accent pinstripe
 * - Official coach typography (22436 · WEC · NDLS-CNB)
 *
 * UV Mapping convention:
 * V = 0.00: Underbody bottom center
 * V = 0.25: Left flank (facing camera)
 * V = 0.50: Top roof centerline
 * V = 0.75: Right flank
 * V = 1.00: Underbody bottom center
 */
export function getCoachTexture(): THREE.CanvasTexture | null {
  if (typeof document === 'undefined') return null;
  if (cachedCoachTexture) return cachedCoachTexture;

  const width = 2048;
  const height = 1024;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  // 1. Base Fuselage: Platinum Silver (#ECEFF1)
  ctx.fillStyle = '#ECEFF1';
  ctx.fillRect(0, 0, width, height);

  // Subtle metallic lighting gradient across flank
  const metalGrad = ctx.createLinearGradient(0, 0, 0, height);
  metalGrad.addColorStop(0.0, 'rgba(255, 255, 255, 0.35)');
  metalGrad.addColorStop(0.25, 'rgba(240, 244, 248, 0.0)');
  metalGrad.addColorStop(0.50, 'rgba(255, 255, 255, 0.45)');
  metalGrad.addColorStop(0.75, 'rgba(240, 244, 248, 0.0)');
  metalGrad.addColorStop(1.0, 'rgba(215, 225, 235, 0.30)');
  ctx.fillStyle = metalGrad;
  ctx.fillRect(0, 0, width, height);

  // 2. Underbody Dark Anthracite Skirt (V = 0..0.12 and 0.88..1.0)
  ctx.fillStyle = '#1E293B';
  ctx.fillRect(0, 0, width, height * 0.12);
  ctx.fillRect(0, height * 0.88, width, height * 0.12);

  // 3. Lower Orange Accent Pinstripes
  ctx.fillStyle = '#EA580C';
  ctx.fillRect(0, height * 0.12, width, height * 0.015);
  ctx.fillRect(0, height * 0.865, width, height * 0.015);

  // 4. Upper Roofline Signal Orange Bands (V = 0.42..0.46 and 0.54..0.58)
  ctx.fillStyle = '#EA580C';
  ctx.fillRect(0, height * 0.42, width, height * 0.045);
  ctx.fillRect(0, height * 0.535, width, height * 0.045);

  // 5. Left Flank Panoramic Passenger Window Band (Centered at V = 0.25)
  // Window band spans V = 0.20 to 0.31
  const yWinTop = height * 0.20;
  const yWinBot = height * 0.31;
  const winBandHeight = yWinBot - yWinTop;

  // Dark tinted glass continuous strip
  ctx.fillStyle = '#090D16';
  ctx.fillRect(width * 0.07, yWinTop, width * 0.86, winBandHeight);

  // 6. 7 Wide Panoramic Passenger Windows with Rounded Corners
  const numWindows = 7;
  const xStart = width * 0.14;
  const xEnd = width * 0.86;
  const totalSpan = xEnd - xStart;
  const winWidth = totalSpan / (numWindows + 0.3);

  for (let i = 0; i < numWindows; i++) {
    const wx = xStart + i * (winWidth * 1.05);
    const ww = winWidth * 0.88;
    const wy = yWinTop + 8;
    const wh = winBandHeight - 16;

    // Window Outer Frame (Fine Silver/Slate Outline)
    ctx.strokeStyle = '#64748B';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.roundRect(wx, wy, ww, wh, 12);
    ctx.stroke();

    // Window Glass Pane (Deep Tinted Cyan/Black)
    ctx.fillStyle = '#0F172A';
    ctx.beginPath();
    ctx.roundRect(wx + 2, wy + 2, ww - 4, wh - 4, 10);
    ctx.fill();

    // Warm Interior Cabin Illumination & Seat Reflection
    const warmGrad = ctx.createLinearGradient(0, wy, 0, wy + wh);
    warmGrad.addColorStop(0.0, 'rgba(254, 240, 138, 0.40)');
    warmGrad.addColorStop(0.4, 'rgba(253, 224, 71, 0.18)');
    warmGrad.addColorStop(1.0, 'rgba(15, 23, 42, 0.90)');
    ctx.fillStyle = warmGrad;
    ctx.beginPath();
    ctx.roundRect(wx + 4, wy + 4, ww - 8, wh - 8, 8);
    ctx.fill();

    // Vertical Center Window Divider
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(wx + ww / 2, wy + 2);
    ctx.lineTo(wx + ww / 2, wy + wh - 2);
    ctx.stroke();
  }

  // 7. Flush Passenger Plug Doors (Front & Rear)
  const drawDoor = (doorX: number, isRightFlank: boolean = false) => {
    const doorW = width * 0.045;
    const doorH = height * 0.16;
    const doorY = isRightFlank ? height * 0.69 - 10 : yWinTop - 10;

    // Door Panel Outline
    ctx.strokeStyle = '#64748B';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.roundRect(doorX, doorY, doorW, doorH, 8);
    ctx.stroke();

    // Door Vision Window
    ctx.fillStyle = '#090D16';
    ctx.beginPath();
    ctx.roundRect(doorX + doorW * 0.22, doorY + 14, doorW * 0.56, doorH * 0.42, 6);
    ctx.fill();
    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Door Status Light (Green / Locked)
    ctx.fillStyle = '#10B981';
    ctx.beginPath();
    ctx.arc(doorX + doorW * 0.5, doorY + doorH * 0.72, 4, 0, Math.PI * 2);
    ctx.fill();
  };

  drawDoor(width * 0.08);
  drawDoor(width * 0.875);

  // 8. Coach Identification Typography
  ctx.fillStyle = '#1E293B';
  ctx.font = 'bold 18px sans-serif';
  ctx.fillText('22436  ·  VANDE BHARAT EXPRESS  ·  WEC', width * 0.38, yWinTop - 14);

  // 9. Right Flank Duplicate (Symmetric Window & Door Band at V = 0.69..0.80)
  const yRightTop = height * 0.69;
  const yRightBot = height * 0.80;
  const rBandHeight = yRightBot - yRightTop;

  ctx.fillStyle = '#090D16';
  ctx.fillRect(width * 0.07, yRightTop, width * 0.86, rBandHeight);

  for (let i = 0; i < numWindows; i++) {
    const wx = xStart + i * (winWidth * 1.05);
    const ww = winWidth * 0.88;
    const wy = yRightTop + 8;
    const wh = rBandHeight - 16;

    ctx.strokeStyle = '#64748B';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.roundRect(wx, wy, ww, wh, 12);
    ctx.stroke();

    ctx.fillStyle = '#0F172A';
    ctx.beginPath();
    ctx.roundRect(wx + 2, wy + 2, ww - 4, wh - 4, 10);
    ctx.fill();

    const warmGrad = ctx.createLinearGradient(0, wy, 0, wy + wh);
    warmGrad.addColorStop(0.0, 'rgba(254, 240, 138, 0.40)');
    warmGrad.addColorStop(0.4, 'rgba(253, 224, 71, 0.18)');
    warmGrad.addColorStop(1.0, 'rgba(15, 23, 42, 0.90)');
    ctx.fillStyle = warmGrad;
    ctx.beginPath();
    ctx.roundRect(wx + 4, wy + 4, ww - 8, wh - 8, 8);
    ctx.fill();
  }

  drawDoor(width * 0.08, true);
  drawDoor(width * 0.875, true);

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.anisotropy = 8;
  texture.needsUpdate = true;
  cachedCoachTexture = texture;
  return texture;
}

/**
 * Procedural Canvas Texture for Aerodynamic Cab Nose:
 * - Seamless continuation of Platinum Silver base (#ECEFF1)
 * - Smooth anti-aliased Signal Orange aerodynamic mask (#EA580C) curving from roofline over cheeks
 * - Panoramic driver cockpit windshield with ceramic frit border (#070B14) & sky reflection on brow
 * - Recessed projector headlamp housing graphics on cheeks
 * - White aerodynamic chin cone & Indian Railways front crest
 *
 * UV Mapping:
 * U = 0: Bulkhead (meets coach body)
 * U = 1: Nose tip
 * V = 0.50: Top roof centerline / cockpit brow
 * V = 0.25: Left cheek
 * V = 0.75: Right cheek
 */
export function getNoseTexture(): THREE.CanvasTexture | null {
  if (typeof document === 'undefined') return null;
  if (cachedNoseTexture) return cachedNoseTexture;

  const width = 1024;
  const height = 1024;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  // 1. Base Fuselage: Platinum Silver (#ECEFF1)
  ctx.fillStyle = '#ECEFF1';
  ctx.fillRect(0, 0, width, height);

  // Subtle metallic lighting gradient
  const metalGrad = ctx.createLinearGradient(0, 0, width, 0);
  metalGrad.addColorStop(0.0, 'rgba(255, 255, 255, 0.35)');
  metalGrad.addColorStop(0.7, 'rgba(240, 244, 248, 0.0)');
  metalGrad.addColorStop(1.0, 'rgba(220, 230, 240, 0.25)');
  ctx.fillStyle = metalGrad;
  ctx.fillRect(0, 0, width, height);

  // 2. Underbody Dark Anthracite Skirt (V = 0..0.12 and 0.88..1.0)
  ctx.fillStyle = '#1E293B';
  ctx.fillRect(0, 0, width, height * 0.12);
  ctx.fillRect(0, height * 0.88, width, height * 0.12);

  // 3. Smooth Aerodynamic Signal Orange Livery Mask (#EA580C)
  // Seamlessly joins the coach roofline band at U=0 (V = 0.42..0.46 and 0.54..0.58)
  // and sweeps forward across the cheeks and brow, terminating before the white chin (U = 0.82)
  ctx.fillStyle = '#EA580C';
  ctx.beginPath();
  // Left roofline at U=0 (y = height * 0.42)
  ctx.moveTo(0, height * 0.42);
  // Sweep down across left cheek
  ctx.bezierCurveTo(width * 0.20, height * 0.26, width * 0.55, height * 0.22, width * 0.78, height * 0.35);
  // Curve around the chin apex
  ctx.bezierCurveTo(width * 0.83, height * 0.42, width * 0.83, height * 0.58, width * 0.78, height * 0.65);
  // Sweep back across right cheek
  ctx.bezierCurveTo(width * 0.55, height * 0.78, width * 0.20, height * 0.74, 0, height * 0.58);
  // Right roofline inner edge at U=0
  ctx.lineTo(0, height * 0.535);
  // Center crown recess
  ctx.bezierCurveTo(width * 0.12, height * 0.52, width * 0.12, height * 0.48, 0, height * 0.465);
  ctx.closePath();
  ctx.fill();

  // 4. Panoramic Driver Cockpit Windshield (U = 0.18..0.56, centered around V = 0.50)
  // Outer Ceramic Black Frit Gasket Border
  ctx.fillStyle = '#050811';
  ctx.beginPath();
  ctx.moveTo(width * 0.18, height * 0.42);
  ctx.bezierCurveTo(width * 0.36, height * 0.39, width * 0.52, height * 0.43, width * 0.56, height * 0.50);
  ctx.bezierCurveTo(width * 0.52, height * 0.57, width * 0.36, height * 0.61, width * 0.18, height * 0.58);
  ctx.closePath();
  ctx.fill();

  // Glossy Windshield Tinted Glass (Deep Midnight Blue with Sky Reflection Gradient)
  const glassGrad = ctx.createLinearGradient(width * 0.20, 0, width * 0.54, 0);
  glassGrad.addColorStop(0.0, '#090D18');
  glassGrad.addColorStop(0.45, '#0F1E38');
  glassGrad.addColorStop(0.85, '#1E293B');
  glassGrad.addColorStop(1.0, '#0A0F1D');
  ctx.fillStyle = glassGrad;
  ctx.beginPath();
  ctx.moveTo(width * 0.20, height * 0.43);
  ctx.bezierCurveTo(width * 0.36, height * 0.41, width * 0.50, height * 0.44, width * 0.54, height * 0.50);
  ctx.bezierCurveTo(width * 0.50, height * 0.56, width * 0.36, height * 0.59, width * 0.20, height * 0.57);
  ctx.closePath();
  ctx.fill();

  // Windshield Center Divider Mullion
  ctx.strokeStyle = '#64748B';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(width * 0.19, height * 0.50);
  ctx.lineTo(width * 0.54, height * 0.50);
  ctx.stroke();

  // 5. Headlamp Housing Graphical Surrounds on Left and Right Cheeks
  const drawHeadlampSurround = (cy: number) => {
    ctx.fillStyle = '#090D16';
    ctx.strokeStyle = '#CBD5E1';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(width * 0.70, cy, 30, 20, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Dual Projector LED Lenses (Bright Diamond Glow)
    ctx.fillStyle = '#F8FAFC';
    ctx.beginPath();
    ctx.arc(width * 0.69, cy, 6, 0, Math.PI * 2);
    ctx.arc(width * 0.71, cy, 6, 0, Math.PI * 2);
    ctx.fill();
  };

  drawHeadlampSurround(height * 0.32); // Left cheek
  drawHeadlampSurround(height * 0.68); // Right cheek

  // 6. Indian Railways Front Crest on White Chin Cone (U = 0.86, V = 0.50)
  ctx.fillStyle = '#1E3A8A';
  ctx.beginPath();
  ctx.arc(width * 0.88, height * 0.50, 14, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#F59E0B';
  ctx.beginPath();
  ctx.arc(width * 0.88, height * 0.50, 7, 0, Math.PI * 2);
  ctx.fill();

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.anisotropy = 8;
  texture.needsUpdate = true;
  cachedNoseTexture = texture;
  return texture;
}
