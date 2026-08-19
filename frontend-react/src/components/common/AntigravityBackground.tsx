import React, { useEffect, useRef } from 'react';

export const AntigravityBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    let animationId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize, { passive: true });

    const isMobile = window.innerWidth < 768;
    const particleCount = isMobile ? 18 : 42;
    const mouse = { x: -1000, y: -1000, radius: 140 };

    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };

    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mouseleave', handleMouseLeave, { passive: true });

    class Particle {
      x: number = 0;
      y: number = 0;
      size: number = 0;
      speedY: number = 0;
      speedX: number = 0;
      alpha: number = 0;
      color: string = '';

      constructor() {
        this.reset();
      }

      reset() {
        this.x = Math.random() * width;
        this.y = height + Math.random() * 80;
        this.size = Math.random() * 2.2 + 1.2;
        this.speedY = Math.random() * 0.7 + 0.35;
        this.speedX = (Math.random() - 0.5) * 0.4;
        this.alpha = Math.random() * 0.6 + 0.35;
        this.color = Math.random() > 0.3 ? '197, 160, 89' : '0, 229, 255'; // Ouro CGCFN ou Ciano Tático
      }

      update() {
        this.y -= this.speedY;
        this.x += this.speedX;

        const dx = mouse.x - this.x;
        const dy = mouse.y - this.y;
        const distSq = dx * dx + dy * dy;

        if (distSq < 19600) {
          // 140^2
          const dist = Math.sqrt(distSq);
          const force = (140 - dist) / 140;
          const angle = Math.atan2(dy, dx);
          this.x -= Math.cos(angle) * force * 3.5;
          this.y -= Math.sin(angle) * force * 3.5;
        }

        if (this.y < -30 || this.x < -30 || this.x > width + 30) {
          this.reset();
        }
      }

      draw(context: CanvasRenderingContext2D) {
        context.save();
        context.fillStyle = `rgba(${this.color}, ${this.alpha})`;
        context.shadowBlur = 8;
        context.shadowColor = `rgba(${this.color}, 0.8)`;
        context.beginPath();
        context.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        context.fill();
        context.restore();
      }
    }

    const particles: Particle[] = Array.from({ length: particleCount }, () => new Particle());

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      particles.forEach((p) => {
        p.update();
        p.draw(ctx);
      });

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0 opacity-80"
    />
  );
};
