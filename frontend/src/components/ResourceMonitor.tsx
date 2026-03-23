"use client";

import { useEffect, useState, useRef } from "react";
import { Cpu, MemoryStick } from "lucide-react";
import type { WSEvent } from "@/hooks/useWebSocket";

type Props = {
  subscribe: (cb: (e: WSEvent) => void) => () => void;
};

const MAX_POINTS = 60;

function Sparkline({ data, color, label, value }: { data: number[]; color: string; label: string; value: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, w, h);

    if (data.length < 2) return;

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    gradient.addColorStop(0, color + "40");
    gradient.addColorStop(1, color + "00");

    const step = w / (MAX_POINTS - 1);
    const startIdx = Math.max(0, data.length - MAX_POINTS);
    const points = data.slice(startIdx);

    ctx.beginPath();
    ctx.moveTo(0, h);
    points.forEach((v, i) => {
      const x = i * step;
      const y = h - (v / 100) * h;
      if (i === 0) ctx.lineTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineTo((points.length - 1) * step, h);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line
    ctx.beginPath();
    points.forEach((v, i) => {
      const x = i * step;
      const y = h - (v / 100) * h;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }, [data, color]);

  return (
    <div className="flex-1 rounded-xl border border-white/10 bg-white/[0.02] p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-white/50">{label}</span>
        <span className="text-sm font-bold" style={{ color }}>
          {value.toFixed(1)}%
        </span>
      </div>
      <canvas ref={canvasRef} className="h-16 w-full" />
    </div>
  );
}

export default function ResourceMonitor({ subscribe }: Props) {
  const [cpuData, setCpuData] = useState<number[]>([]);
  const [ramData, setRamData] = useState<number[]>([]);

  useEffect(() => {
    const unsub = subscribe((event) => {
      if (event.type !== "resource_stats") return;
      setCpuData((prev) => [...prev.slice(-(MAX_POINTS + 1)), event.cpu as number]);
      setRamData((prev) => [...prev.slice(-(MAX_POINTS + 1)), event.ram as number]);
    });
    return unsub;
  }, [subscribe]);

  const currentCpu = cpuData[cpuData.length - 1] ?? 0;
  const currentRam = ramData[ramData.length - 1] ?? 0;

  return (
    <div className="rounded-2xl border border-white/10 bg-black/40 p-4 backdrop-blur-sm">
      <div className="mb-3 flex items-center gap-2">
        <Cpu className="h-4 w-4 text-purple-400" />
        <h3 className="text-sm font-semibold text-white/80">System Resources</h3>
      </div>
      <div className="flex gap-3">
        <Sparkline data={cpuData} color="#22d3ee" label="CPU" value={currentCpu} />
        <Sparkline data={ramData} color="#a78bfa" label="RAM" value={currentRam} />
      </div>
    </div>
  );
}
