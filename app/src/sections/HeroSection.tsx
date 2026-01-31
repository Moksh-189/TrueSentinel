import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Button } from '@/components/ui/button';
import { ArrowRight, Play, CheckCircle2 } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

export function HeroSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLDivElement>(null);
  const glassCardRef = useRef<HTMLDivElement>(null);
  const scanLineRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const bg = bgRef.current;
    const headline = headlineRef.current;
    const glassCard = glassCardRef.current;
    const scanLine = scanLineRef.current;

    if (!section || !bg || !headline || !glassCard || !scanLine) return;

    const ctx = gsap.context(() => {
      // Auto-play entrance animation (on page load)
      const entranceTl = gsap.timeline({ defaults: { ease: 'power2.out' } });

      entranceTl
        .fromTo(bg, { opacity: 0 }, { opacity: 1, duration: 0.4 }, 0)
        .fromTo(
          headline.children,
          { y: 26, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.5, stagger: 0.1 },
          0.15
        )
        .fromTo(
          glassCard,
          { x: '10vw', opacity: 0 },
          { x: 0, opacity: 1, duration: 0.5 },
          0.55
        );

      // Scroll-driven exit animation (pinned)
      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: 'top top',
          end: '+=130%',
          pin: true,
          scrub: 0.6,
          onLeaveBack: () => {
            // Reset to visible state when scrolling back to top
            gsap.set([bg, headline, glassCard], { opacity: 1, x: 0, y: 0, scale: 1 });
          },
        },
      });

      // Background parallax and fade
      scrollTl.fromTo(
        bg,
        { scale: 1 },
        { scale: 1.1, opacity: 0.25, ease: 'none' },
        0.7
      );

      // Headline exit
      scrollTl.fromTo(
        headline,
        { y: 0, opacity: 1 },
        { y: '-18vh', opacity: 0, ease: 'power2.in' },
        0.7
      );

      // Glass card exit
      scrollTl.fromTo(
        glassCard,
        { y: 0, opacity: 1 },
        { y: '16vh', opacity: 0, ease: 'power2.in' },
        0.7
      );

      // Scan line fade
      scrollTl.fromTo(scanLine, { opacity: 1 }, { opacity: 0 }, 0.85);
    }, section);

    return () => ctx.revert();
  }, []);

  const scrollToDemo = () => {
    const element = document.getElementById('phishing-shield');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section
      ref={sectionRef}
      id="hero"
      className="section-pinned z-10"
    >
      {/* Background Image */}
      <div
        ref={bgRef}
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: 'url(/images/hero_lab.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />

      {/* Dot Grid Overlay */}
      <div className="absolute inset-0 dot-grid opacity-[0.08] z-[1] pointer-events-none" />

      {/* Vignette Overlay */}
      <div className="absolute inset-0 vignette z-[2] pointer-events-none" />

      {/* Scan Line */}
      <div ref={scanLineRef} className="scan-line z-[4] pointer-events-none" />

      {/* Headline Block */}
      <div
        ref={headlineRef}
        className="absolute left-[9vw] top-[18vh] w-[82vw] z-[5]"
      >
        <h1 className="text-[44px] md:text-[64px] lg:text-[80px] font-bold text-[#F4F7FB] leading-[1.05] mb-6">
          Verify the signal.
        </h1>
        <p className="text-lg md:text-xl text-[#A9B3C2] max-w-2xl mb-8 leading-relaxed">
          AI-powered detection for phishing and deepfake threats—fast, private, explainable.
        </p>
        <div className="flex flex-wrap gap-4">
          <Button
            onClick={scrollToDemo}
            className="bg-[#27D3F3] text-[#0B0F17] hover:bg-[#27D3F3]/90 font-medium px-6 py-3 text-base"
          >
            Get Started
            <ArrowRight className="ml-2 w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            onClick={scrollToDemo}
            className="border-white/20 text-[#F4F7FB] hover:bg-white/5 px-6 py-3 text-base"
          >
            <Play className="mr-2 w-4 h-4" />
            View Demo
          </Button>
        </div>
      </div>

      {/* Glass Status Card */}
      <div
        ref={glassCardRef}
        className="absolute right-[6vw] bottom-[8vh] w-[34vw] min-w-[320px] max-w-[420px] z-[6]"
      >
        <div className="glass-panel p-6">
          <span className="micro-label block mb-4">SYSTEM STATUS</span>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#A9B3C2]">Threat DB</span>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#27F3A8] animate-pulse" />
                <span className="text-sm text-[#27F3A8]">Live</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#A9B3C2]">Model</span>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#27F3A8] animate-pulse" />
                <span className="text-sm text-[#27F3A8]">Online</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#A9B3C2]">Privacy</span>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#27D3F3]" />
                <span className="text-sm text-[#27D3F3]">On-device ready</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
