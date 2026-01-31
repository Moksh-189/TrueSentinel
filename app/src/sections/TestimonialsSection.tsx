import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Quote } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const testimonials = [
  {
    quote: 'We cut phishing response time by 70%. The Bloom Filter approach means zero latency for known threats.',
    author: 'Security Lead',
    company: 'Fintech',
    initials: 'SL',
    color: '#27D3F3',
  },
  {
    quote: 'Deepfake checks now happen in the background, seamlessly. Our users never notice the protection.',
    author: 'Trust & Safety Manager',
    company: 'Social Platform',
    initials: 'TS',
    color: '#27F3A8',
  },
];

export function TestimonialsSection() {
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
          { y: 40, opacity: 0 },
          {
            y: 0,
            opacity: 1,
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
      id="testimonials"
      className="section-flowing z-[80] bg-[#0B0F17] py-20"
    >
      {/* Dot Grid Overlay */}
      <div className="absolute inset-0 dot-grid opacity-[0.06] pointer-events-none" />

      <div className="relative max-w-[980px] mx-auto px-6">
        {/* Heading */}
        <div ref={headingRef} className="text-center mb-12">
          <h2 className="text-[32px] md:text-[42px] lg:text-[48px] font-bold text-[#F4F7FB] mb-4">
            What teams say.
          </h2>
        </div>

        {/* Testimonial Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {testimonials.map((testimonial, index) => (
            <div
              key={testimonial.author}
              ref={(el) => { cardsRef.current[index] = el; }}
              className="glass-panel p-6 md:p-8"
            >
              {/* Quote Icon */}
              <div className="mb-4">
                <Quote 
                  className="w-8 h-8"
                  style={{ color: testimonial.color, opacity: 0.5 }}
                />
              </div>
              
              {/* Quote Text */}
              <p className="text-lg text-[#F4F7FB] leading-relaxed mb-6">
                "{testimonial.quote}"
              </p>
              
              {/* Author */}
              <div className="flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center font-medium text-sm"
                  style={{ 
                    backgroundColor: `${testimonial.color}20`,
                    color: testimonial.color,
                  }}
                >
                  {testimonial.initials}
                </div>
                <div>
                  <span className="block text-sm text-[#F4F7FB] font-medium">
                    {testimonial.author}
                  </span>
                  <span className="text-xs text-[#A9B3C2]">
                    {testimonial.company}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
