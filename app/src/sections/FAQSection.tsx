import { useRef, useLayoutEffect, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Plus, Minus } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const faqs = [
  {
    question: 'Do you store URLs or media?',
    answer: 'No. Trust-Sentinel processes everything on-device or in ephemeral memory. We never persist raw URLs or media files. Only anonymized feature vectors may be stored for model improvement, and only with your explicit consent.',
  },
  {
    question: 'Can I run this on-device?',
    answer: 'Yes. Our models are optimized for edge deployment. The phishing detector uses Bloom Filters that fit in under 10MB, and the deepfake shield runs on TensorFlow Lite with ~45MB model size.',
  },
  {
    question: "What's the false positive rate?",
    answer: 'Our phishing detector maintains a sub-0.3% false positive rate on verified datasets. The deepfake shield achieves 98%+ accuracy on publicly available deepfake benchmarks.',
  },
  {
    question: 'How do I integrate?',
    answer: 'We offer REST APIs, WebSocket streams, and SDKs for Python, Node.js, and Go. Most teams are up and running within a single sprint.',
  },
  {
    question: 'Is there an SLA?',
    answer: 'Enterprise plans include a 99.9% uptime SLA with dedicated support channels. Team plans include priority support with 24-hour response time.',
  },
];

export function FAQSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLDivElement>(null);
  const itemsRef = useRef<(HTMLDivElement | null)[]>([]);
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const heading = headingRef.current;
    const items = itemsRef.current.filter(Boolean);

    if (!section || !heading || items.length === 0) return;

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

      // Items staggered reveal
      items.forEach((item) => {
        gsap.fromTo(
          item,
          { y: 24, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            scrollTrigger: {
              trigger: item,
              start: 'top 85%',
              end: 'top 65%',
              scrub: 0.3,
            },
          }
        );
      });
    }, section);

    return () => ctx.revert();
  }, []);

  const toggleItem = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section
      ref={sectionRef}
      id="faq"
      className="section-flowing z-[100] bg-[#0B0F17] py-20"
    >
      <div className="max-w-[800px] mx-auto px-6">
        {/* Heading */}
        <div ref={headingRef} className="text-center mb-12">
          <h2 className="text-[32px] md:text-[42px] lg:text-[48px] font-bold text-[#F4F7FB] mb-4">
            Answers.
          </h2>
        </div>

        {/* FAQ Items */}
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div
              key={faq.question}
              ref={(el) => { itemsRef.current[index] = el; }}
              className="glass-panel rounded-2xl overflow-hidden"
            >
              <button
                onClick={() => toggleItem(index)}
                className="w-full flex items-center justify-between p-5 text-left"
              >
                <span className="text-[#F4F7FB] font-medium pr-4">
                  {faq.question}
                </span>
                <div 
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all ${
                    openIndex === index 
                      ? 'bg-[#27D3F3]/20 rotate-0' 
                      : 'bg-white/5 rotate-0'
                  }`}
                >
                  {openIndex === index ? (
                    <Minus className="w-4 h-4 text-[#27D3F3]" />
                  ) : (
                    <Plus className="w-4 h-4 text-[#A9B3C2]" />
                  )}
                </div>
              </button>
              
              <div 
                className={`overflow-hidden transition-all duration-300 ease-out ${
                  openIndex === index ? 'max-h-96' : 'max-h-0'
                }`}
              >
                <div className="px-5 pb-5">
                  <p className="text-[#A9B3C2] leading-relaxed">
                    {faq.answer}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
