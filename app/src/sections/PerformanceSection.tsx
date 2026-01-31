import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Zap, Package, Shield } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const metrics = [
  {
    label: 'Detection time',
    value: '<100ms',
    icon: Zap,
    color: '#27D3F3',
    progress: 95,
  },
  {
    label: 'Model size',
    value: '~1MB',
    icon: Package,
    color: '#27F3A8',
    progress: 98,
  },
  {
    label: 'Privacy mode',
    value: 'On-device',
    icon: Shield,
    color: '#27D3F3',
    progress: 100,
  },
];

export function PerformanceSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLDivElement>(null);
  const metricsCardRef = useRef<HTMLDivElement>(null);
  const progressRefs = useRef<(HTMLDivElement | null)[]>([]);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const bg = bgRef.current;
    const headline = headlineRef.current;
    const metricsCard = metricsCardRef.current;
    const progressBars = progressRefs.current.filter(Boolean);

    if (!section || !bg || !headline || !metricsCard) return;

    const ctx = gsap.context(() => {
      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: 'top top',
          end: '+=130%',
          pin: true,
          scrub: 0.6,
        },
      });

      // Background entrance
      scrollTl.fromTo(
        bg,
        { scale: 1.12, opacity: 0.7 },
        { scale: 1, opacity: 1, ease: 'none' },
        0
      );
      scrollTl.fromTo(
        bg,
        { scale: 1 },
        { scale: 1.1, opacity: 0.3, ease: 'none' },
        0.7
      );

      // Headline entrance from left
      scrollTl.fromTo(
        headline,
        { x: '-55vw', opacity: 0 },
        { x: 0, opacity: 1, ease: 'power2.out' },
        0
      );
      scrollTl.fromTo(
        headline,
        { x: 0, opacity: 1 },
        { x: '-18vw', opacity: 0, ease: 'power2.in' },
        0.7
      );

      // Metrics card entrance from right
      scrollTl.fromTo(
        metricsCard,
        { x: '55vw', opacity: 0 },
        { x: 0, opacity: 1, ease: 'power2.out' },
        0.06
      );
      scrollTl.fromTo(
        metricsCard,
        { x: 0, opacity: 1 },
        { x: '18vw', opacity: 0, ease: 'power2.in' },
        0.7
      );

      // Progress bars animate
      progressBars.forEach((bar, i) => {
        scrollTl.fromTo(
          bar,
          { scaleX: 0 },
          { scaleX: 1, ease: 'none' },
          0.14 + i * 0.03
        );
      });
    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={sectionRef}
      id="performance"
      className="section-pinned z-[60]"
    >
      {/* Background Image */}
      <div
        ref={bgRef}
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: 'url(/images/data_center_corridor.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.7,
        }}
      />

      {/* Dot Grid Overlay */}
      <div className="absolute inset-0 dot-grid opacity-[0.08] z-[1] pointer-events-none" />

      {/* Vignette Overlay */}
      <div className="absolute inset-0 vignette z-[2] pointer-events-none" />

      {/* Left Headline */}
      <div
        ref={headlineRef}
        className="absolute left-[9vw] top-[18vh] w-[36vw] z-[5]"
      >
        <h2 className="text-[36px] md:text-[48px] lg:text-[56px] font-bold text-[#F4F7FB] leading-[1.1] mb-6">
          Built for speed.
        </h2>
        <p className="text-base md:text-lg text-[#A9B3C2] leading-relaxed">
          Sub-100ms decisions. Lightweight models. On-device options.
        </p>
      </div>

      {/* Right Metrics Card */}
      <div
        ref={metricsCardRef}
        className="absolute right-[6vw] top-[18vh] w-[40vw] min-w-[340px] max-w-[480px] z-[6]"
      >
        <div className="glass-panel p-6">
          <div className="space-y-6">
            {metrics.map((metric, index) => {
              const Icon = metric.icon;
              return (
                <div key={metric.label} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: `${metric.color}15` }}
                      >
                        <Icon className="w-5 h-5" style={{ color: metric.color }} />
                      </div>
                      <span className="text-[#F4F7FB] font-medium">{metric.label}</span>
                    </div>
                    <span
                      className="font-mono text-lg font-bold"
                      style={{ color: metric.color }}
                    >
                      {metric.value}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                    <div
                      ref={(el) => { progressRefs.current[index] = el; }}
                      className="h-full rounded-full origin-left"
                      style={{
                        width: `${metric.progress}%`,
                        backgroundColor: metric.color,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Additional Stats */}
          <div className="mt-6 pt-6 border-t border-white/10 grid grid-cols-3 gap-4">
            <div className="text-center">
              <span className="micro-label block mb-1">THROUGHPUT</span>
              <span className="font-mono text-lg text-[#27D3F3]">10K/s</span>
            </div>
            <div className="text-center">
              <span className="micro-label block mb-1">UPTIME</span>
              <span className="font-mono text-lg text-[#27F3A8]">99.9%</span>
            </div>
            <div className="text-center">
              <span className="micro-label block mb-1">LATENCY</span>
              <span className="font-mono text-lg text-[#27D3F3]">12ms</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
