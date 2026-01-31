import { useRef, useLayoutEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Button } from '@/components/ui/button';
import { Check, Zap, Building2 } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const plans = [
  {
    name: 'Starter',
    price: 'Free',
    description: 'For personal use and small projects',
    icon: Zap,
    color: '#A9B3C2',
    features: [
      '1,000 checks/mo',
      'Phishing detection',
      'Community support',
      'Basic API access',
    ],
    cta: 'Start free',
    highlighted: false,
  },
  {
    name: 'Team',
    price: '$49',
    period: '/mo',
    description: 'For growing security teams',
    icon: Zap,
    color: '#27D3F3',
    features: [
      '50,000 checks/mo',
      'Deepfake detection',
      'Priority support',
      'SSO integration',
      'Advanced analytics',
    ],
    cta: 'Start trial',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    description: 'For large organizations',
    icon: Building2,
    color: '#27F3A8',
    features: [
      'Unlimited checks',
      'Custom models',
      'Dedicated infrastructure',
      'SLA guarantee',
      '24/7 support',
    ],
    cta: 'Contact sales',
    highlighted: false,
  },
];

export function PricingSection() {
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
      id="pricing"
      className="section-flowing z-[90] bg-[#0B0F17] py-20"
    >
      <div className="max-w-[1040px] mx-auto px-6">
        {/* Heading */}
        <div ref={headingRef} className="text-center mb-12">
          <h2 className="text-[32px] md:text-[42px] lg:text-[48px] font-bold text-[#F4F7FB] mb-4">
            Start free. Scale safe.
          </h2>
          <p className="text-base md:text-lg text-[#A9B3C2] max-w-xl mx-auto">
            Choose the plan that fits your security needs.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan, index) => {
            const Icon = plan.icon;
            return (
              <div
                key={plan.name}
                ref={(el) => { cardsRef.current[index] = el; }}
                className={`glass-panel p-6 md:p-8 ${
                  plan.highlighted 
                    ? 'border-[#27D3F3]/50 relative' 
                    : ''
                }`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="px-3 py-1 rounded-full bg-[#27D3F3] text-[#0B0F17] text-xs font-medium">
                      Most Popular
                    </span>
                  </div>
                )}
                
                {/* Plan Header */}
                <div className="mb-6">
                  <div 
                    className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
                    style={{ backgroundColor: `${plan.color}15` }}
                  >
                    <Icon className="w-5 h-5" style={{ color: plan.color }} />
                  </div>
                  <h3 className="text-xl font-semibold text-[#F4F7FB] mb-1">
                    {plan.name}
                  </h3>
                  <p className="text-sm text-[#A9B3C2]">{plan.description}</p>
                </div>
                
                {/* Price */}
                <div className="mb-6">
                  <span className="text-3xl font-bold text-[#F4F7FB]">
                    {plan.price}
                  </span>
                  {plan.period && (
                    <span className="text-[#A9B3C2]">{plan.period}</span>
                  )}
                </div>
                
                {/* Features */}
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-3">
                      <Check className="w-4 h-4 text-[#27F3A8]" />
                      <span className="text-sm text-[#A9B3C2]">{feature}</span>
                    </li>
                  ))}
                </ul>
                
                {/* CTA */}
                <Button
                  className={`w-full ${
                    plan.highlighted
                      ? 'bg-[#27D3F3] text-[#0B0F17] hover:bg-[#27D3F3]/90'
                      : 'border-white/20 text-[#F4F7FB] hover:bg-white/5'
                  }`}
                  variant={plan.highlighted ? 'default' : 'outline'}
                >
                  {plan.cta}
                </Button>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
