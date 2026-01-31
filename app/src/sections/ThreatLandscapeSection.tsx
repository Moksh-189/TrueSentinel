import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Globe, ScanFace, Activity, Database, Clock, Shield } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

export function ThreatLandscapeSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const tickerRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const bg = bgRef.current;
    const headline = headlineRef.current;
    const card = cardRef.current;
    const ticker = tickerRef.current;

    if (!section || !bg || !headline || !card || !ticker) return;

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
        { scale: 1.12, opacity: 0.6 },
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
        { x: '-50vw', opacity: 0 },
        { x: 0, opacity: 1, ease: 'power2.out' },
        0
      );
      scrollTl.fromTo(
        headline,
        { x: 0, opacity: 1 },
        { x: '-18vw', opacity: 0, ease: 'power2.in' },
        0.7
      );

      // Card entrance from right
      scrollTl.fromTo(
        card,
        { x: '50vw', opacity: 0 },
        { x: 0, opacity: 1, ease: 'power2.out' },
        0.06
      );
      scrollTl.fromTo(
        card,
        { x: 0, opacity: 1 },
        { x: '18vw', opacity: 0, ease: 'power2.in' },
        0.7
      );

      // Ticker entrance from bottom
      scrollTl.fromTo(
        ticker,
        { y: '30vh', opacity: 0 },
        { y: 0, opacity: 1, ease: 'power2.out' },
        0.1
      );
      scrollTl.fromTo(
        ticker,
        { y: 0, opacity: 1 },
        { y: '18vh', opacity: 0, ease: 'power2.in' },
        0.7
      );
    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={sectionRef}
      id="threat-landscape"
      className="section-pinned z-20"
    >
      {/* Background Image */}
      <div
        ref={bgRef}
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: 'url(/images/threat_map.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.6,
        }}
      />

      {/* Dot Grid Overlay */}
      <div className="absolute inset-0 dot-grid opacity-[0.08] z-[1] pointer-events-none" />

      {/* Vignette Overlay */}
      <div className="absolute inset-0 vignette z-[2] pointer-events-none" />

      {/* Left Headline */}
      <div
        ref={headlineRef}
        className="absolute left-[9vw] top-[18vh] w-[38vw] z-[5]"
      >
        <h2 className="text-[36px] md:text-[48px] lg:text-[56px] font-bold text-[#F4F7FB] leading-[1.1] mb-6">
          The modern attack surface.
        </h2>
        <p className="text-base md:text-lg text-[#A9B3C2] leading-relaxed">
          Phishing links move fast. Deepfakes move faster. You need a signal you can trust.
        </p>
      </div>

      {/* Right Glass Card */}
      <div
        ref={cardRef}
        className="absolute right-[6vw] top-[22vh] w-[34vw] min-w-[300px] max-w-[400px] z-[6]"
      >
        <div className="glass-panel p-6">
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/5">
              <div className="w-10 h-10 rounded-lg bg-[#27D3F3]/10 flex items-center justify-center">
                <Globe className="w-5 h-5 text-[#27D3F3]" />
              </div>
              <div>
                <span className="block text-[#F4F7FB] font-medium">Phishing</span>
                <span className="text-sm text-[#A9B3C2]">Malicious URLs & domains</span>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/5">
              <div className="w-10 h-10 rounded-lg bg-[#27F3A8]/10 flex items-center justify-center">
                <ScanFace className="w-5 h-5 text-[#27F3A8]" />
              </div>
              <div>
                <span className="block text-[#F4F7FB] font-medium">Deepfakes</span>
                <span className="text-sm text-[#A9B3C2]">Synthetic media detection</span>
              </div>
            </div>
          </div>
          <p className="mt-4 text-sm text-[#A9B3C2] text-center">
            Real-time detection for both vectors.
          </p>
        </div>
      </div>

      {/* Bottom Ticker Strip */}
      <div
        ref={tickerRef}
        className="absolute left-[6vw] right-[6vw] bottom-[10vh] z-[7]"
      >
        <div className="glass-panel p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-3">
              <Activity className="w-4 h-4 text-[#27D3F3]" />
              <div>
                <span className="micro-label block">URLs ANALYZED</span>
                <span className="text-lg font-mono text-[#F4F7FB]">2.4M+</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Database className="w-4 h-4 text-[#27F3A8]" />
              <div>
                <span className="micro-label block">INFERENCES</span>
                <span className="text-lg font-mono text-[#F4F7FB]">847K</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Shield className="w-4 h-4 text-[#27D3F3]" />
              <div>
                <span className="micro-label block">FALSE POSITIVE</span>
                <span className="text-lg font-mono text-[#F4F7FB]">0.3%</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Clock className="w-4 h-4 text-[#27F3A8]" />
              <div>
                <span className="micro-label block">AVG RESPONSE</span>
                <span className="text-lg font-mono text-[#F4F7FB]">&lt;100ms</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
