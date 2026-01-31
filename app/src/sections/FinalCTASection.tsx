import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Button } from '@/components/ui/button';
import { ArrowRight, MessageSquare } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

export function FinalCTASection() {
  const sectionRef = useRef<HTMLElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const ctaBlockRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const bg = bgRef.current;
    const ctaBlock = ctaBlockRef.current;

    if (!section || !bg || !ctaBlock) return;

    const ctx = gsap.context(() => {
      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: 'top top',
          end: '+=120%',
          pin: true,
          scrub: 0.6,
        },
      });

      // Background entrance
      scrollTl.fromTo(
        bg,
        { scale: 1.10, opacity: 0.7 },
        { scale: 1, opacity: 1, ease: 'none' },
        0
      );
      scrollTl.fromTo(
        bg,
        { scale: 1 },
        { scale: 1.08, opacity: 0.35, ease: 'none' },
        0.7
      );

      // CTA block entrance from bottom
      scrollTl.fromTo(
        ctaBlock,
        { y: '40vh', opacity: 0 },
        { y: 0, opacity: 1, ease: 'power2.out' },
        0
      );
      scrollTl.fromTo(
        ctaBlock,
        { y: 0, opacity: 1 },
        { y: '-12vh', opacity: 0, ease: 'power2.in' },
        0.7
      );
    }, section);

    return () => ctx.revert();
  }, []);

  const scrollToContact = () => {
    const element = document.getElementById('contact');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section
      ref={sectionRef}
      id="final-cta"
      className="section-pinned z-[110]"
    >
      {/* Background Image */}
      <div
        ref={bgRef}
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: 'url(/images/abstract_data_wave.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.7,
        }}
      />

      {/* Dot Grid Overlay */}
      <div className="absolute inset-0 dot-grid opacity-[0.08] z-[1] pointer-events-none" />

      {/* Vignette Overlay */}
      <div className="absolute inset-0 vignette z-[2] pointer-events-none" />

      {/* Center CTA Block */}
      <div
        ref={ctaBlockRef}
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-[920px] text-center z-[5]"
      >
        <h2 className="text-[36px] md:text-[52px] lg:text-[64px] font-bold text-[#F4F7FB] leading-[1.1] mb-6">
          Ready to verify?
        </h2>
        <p className="text-lg md:text-xl text-[#A9B3C2] max-w-xl mx-auto mb-8">
          Start free. Integrate in minutes. Protect everything.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Button
            onClick={scrollToContact}
            className="bg-[#27D3F3] text-[#0B0F17] hover:bg-[#27D3F3]/90 font-medium px-8 py-3 text-base"
          >
            Get Started
            <ArrowRight className="ml-2 w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            onClick={scrollToContact}
            className="border-white/20 text-[#F4F7FB] hover:bg-white/5 px-8 py-3 text-base"
          >
            <MessageSquare className="mr-2 w-4 h-4" />
            Contact Sales
          </Button>
        </div>
      </div>
    </section>
  );
}
