import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Search, Brain, CheckCircle, Activity } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const steps = [
  {
    number: '01',
    title: 'Inspect',
    description: 'Extract signals from URLs and media without uploading raw data. Privacy-first analysis that keeps your content on-device.',
    icon: Search,
    color: '#27D3F3',
  },
  {
    number: '02',
    title: 'Analyze',
    description: 'Run lightweight models to score risk and detect synthetic artifacts. Sub-100ms inference with explainable results.',
    icon: Brain,
    color: '#27F3A8',
  },
  {
    number: '03',
    title: 'Decide',
    description: 'Return clear actions with evidence—block, review, or approve. Audit-ready logs for compliance and transparency.',
    icon: CheckCircle,
    color: '#27D3F3',
  },
];

export function HowItWorksSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const heading = headingRef.current;
    const cards = cardsRef.current.filter(Boolean);

    if (!section || !heading || cards.length === 0) return;

    const ctx = gsap.context(() => {
      // Heading reveal
      gsap.fromTo(
        heading,
        { y: 24, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          scrollTrigger: {
            trigger: heading,
            start: 'top 80%',
            end: 'top 50%',
            scrub: 0.3,
          },
        }
      );

      // Cards staggered reveal
      cards.forEach((card) => {
        gsap.fromTo(
          card,
          { y: 40, opacity: 0, scale: 0.98 },
          {
            y: 0,
            opacity: 1,
            scale: 1,
            scrollTrigger: {
              trigger: card,
              start: 'top 80%',
              end: 'top 55%',
              scrub: 0.3,
            },
          }
        );
      });
    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={sectionRef}
      id="how-it-works"
      className="section-flowing z-50 bg-[#0B0F17] py-20"
    >
      {/* Subtle radial glow */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 50% 0%, rgba(39, 211, 243, 0.08) 0%, transparent 50%)',
        }}
      />

      <div className="relative max-w-[980px] mx-auto px-6">
        {/* Heading */}
        <div ref={headingRef} className="text-center mb-12">
          <h2 className="text-[32px] md:text-[42px] lg:text-[48px] font-bold text-[#F4F7FB] mb-4">
            Three layers of verification.
          </h2>
          <p className="text-base md:text-lg text-[#A9B3C2] max-w-xl mx-auto">
            Each check is fast, explainable, and privacy-first.
          </p>
        </div>

        {/* Step Cards */}
        <div className="space-y-6">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const offsetClass = index === 1 ? 'md:ml-[8%]' : '';
            
            return (
              <div
                key={step.number}
                ref={(el) => { cardsRef.current[index] = el; }}
                className={`glass-panel p-6 md:p-8 ${offsetClass}`}
              >
                <div className="flex flex-col md:flex-row md:items-start gap-6">
                  {/* Number & Icon */}
                  <div className="flex items-center gap-4 md:w-48 shrink-0">
                    <span 
                      className="font-mono text-3xl font-bold"
                      style={{ color: step.color }}
                    >
                      {step.number}
                    </span>
                    <div 
                      className="w-12 h-12 rounded-xl flex items-center justify-center"
                      style={{ backgroundColor: `${step.color}15` }}
                    >
                      <Icon className="w-6 h-6" style={{ color: step.color }} />
                    </div>
                  </div>
                  
                  {/* Content */}
                  <div className="flex-1">
                    <h3 className="text-xl md:text-2xl font-semibold text-[#F4F7FB] mb-2">
                      {step.title}
                    </h3>
                    <p className="text-[#A9B3C2] leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                  
                  {/* Decorative UI Snippet */}
                  <div className="hidden md:block shrink-0">
                    {index === 0 && (
                      <div className="w-24 h-12 rounded-lg bg-white/5 flex items-center justify-center gap-2">
                        <Activity className="w-4 h-4 text-[#27D3F3]" />
                        <span className="font-mono text-xs text-[#27D3F3]">LIVE</span>
                      </div>
                    )}
                    {index === 1 && (
                      <div className="w-24 h-12 rounded-lg bg-[#27F3A8]/10 flex items-center justify-center">
                        <span className="font-mono text-xs text-[#27F3A8]">&lt;100ms</span>
                      </div>
                    )}
                    {index === 2 && (
                      <div className="w-24 h-12 rounded-lg bg-white/5 flex items-center justify-center gap-2">
                        <CheckCircle className="w-4 h-4 text-[#27D3F3]" />
                        <span className="font-mono text-xs text-[#27D3F3]">PASS</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
