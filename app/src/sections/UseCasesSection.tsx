import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Shield, Users, FileCheck, ArrowRight } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const useCases = [
  {
    title: 'Security Operations',
    description: 'Triage links and attachments at scale. Automate threat detection in your SOC workflow with explainable results.',
    icon: Shield,
    color: '#27D3F3',
  },
  {
    title: 'Trust & Safety',
    description: 'Verify user-generated video without friction. Protect your platform from synthetic media abuse.',
    icon: Users,
    color: '#27F3A8',
  },
  {
    title: 'Compliance',
    description: 'Audit-ready logs and explainable decisions. Meet regulatory requirements with confidence.',
    icon: FileCheck,
    color: '#27D3F3',
  },
];

export function UseCasesSection() {
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
      id="use-cases"
      className="section-flowing z-[70] bg-[#121A26] py-20"
    >
      <div className="max-w-[1100px] mx-auto px-6">
        {/* Heading */}
        <div ref={headingRef} className="text-center mb-12">
          <h2 className="text-[32px] md:text-[42px] lg:text-[48px] font-bold text-[#F4F7FB] mb-4">
            Security, trust, compliance.
          </h2>
          <p className="text-base md:text-lg text-[#A9B3C2] max-w-xl mx-auto">
            Real-world applications for modern security teams.
          </p>
        </div>

        {/* Use Case Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {useCases.map((useCase, index) => {
            const Icon = useCase.icon;
            return (
              <div
                key={useCase.title}
                ref={(el) => { cardsRef.current[index] = el; }}
                className="glass-panel p-6 group hover:-translate-y-1.5 transition-transform duration-300"
              >
                {/* Icon */}
                <div 
                  className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                  style={{ backgroundColor: `${useCase.color}15` }}
                >
                  <Icon className="w-6 h-6" style={{ color: useCase.color }} />
                </div>
                
                {/* Content */}
                <h3 className="text-xl font-semibold text-[#F4F7FB] mb-3">
                  {useCase.title}
                </h3>
                <p className="text-[#A9B3C2] leading-relaxed mb-4">
                  {useCase.description}
                </p>
                
                {/* Link */}
                <button className="flex items-center gap-2 text-sm font-medium group-hover:gap-3 transition-all" style={{ color: useCase.color }}>
                  <span>Learn more</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
