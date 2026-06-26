import { useEffect, useRef } from "react";

const COLORS = ["#2563eb", "#3b82f6", "#22c55e", "#eab308", "#ec4899", "#a855f7"];

interface Piece {
  x: number;
  y: number;
  vx: number;
  vy: number;
  rot: number;
  vrot: number;
  size: number;
  color: string;
}

/** A one-shot confetti burst that fades out, then stops animating. */
export function Confetti({ durationMs = 2600 }: { durationMs?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = (canvas.width = window.innerWidth * dpr);
    const h = (canvas.height = window.innerHeight * dpr);
    ctx.scale(dpr, dpr);
    const vw = window.innerWidth;

    const pieces: Piece[] = Array.from({ length: 160 }, () => ({
      x: vw / 2 + (Math.random() - 0.5) * 200,
      y: -20,
      vx: (Math.random() - 0.5) * 14,
      vy: Math.random() * 6 + 2,
      rot: Math.random() * Math.PI,
      vrot: (Math.random() - 0.5) * 0.3,
      size: Math.random() * 7 + 4,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
    }));

    const start = performance.now();
    let raf = 0;

    const tick = (now: number) => {
      const elapsed = now - start;
      const alpha = Math.max(0, 1 - elapsed / durationMs);
      ctx.clearRect(0, 0, w, h);
      ctx.globalAlpha = alpha;
      for (const p of pieces) {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.18;
        p.vx *= 0.99;
        p.rot += p.vrot;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
        ctx.restore();
      }
      if (elapsed < durationMs) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [durationMs]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-[60] h-full w-full"
    />
  );
}
