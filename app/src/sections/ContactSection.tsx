import { useRef, useLayoutEffect, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Mail, Clock, Send, Shield } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

export function ContactSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const formRef = useRef<HTMLDivElement>(null);
  const infoRef = useRef<HTMLDivElement>(null);
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const form = formRef.current;
    const info = infoRef.current;

    if (!section || !form || !info) return;

    const ctx = gsap.context(() => {
      // Form reveal
      gsap.fromTo(
        form,
        { y: 30, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          scrollTrigger: {
            trigger: form,
            start: 'top 80%',
            end: 'top 55%',
            scrub: 0.3,
          },
        }
      );

      // Info reveal
      gsap.fromTo(
        info,
        { y: 20, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          scrollTrigger: {
            trigger: info,
            start: 'top 80%',
            end: 'top 60%',
            scrub: 0.3,
          },
        }
      );
    }, section);

    return () => ctx.revert();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    // Simulate form submission
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmitted(true);
      setFormData({ name: '', email: '', message: '' });
    }, 1500);
  };

  return (
    <section
      ref={sectionRef}
      id="contact"
      className="section-flowing z-[120] bg-[#0B0F17] py-20"
    >
      <div className="max-w-[980px] mx-auto px-6">
        {/* Heading */}
        <div className="text-center mb-12">
          <h2 className="text-[32px] md:text-[42px] lg:text-[48px] font-bold text-[#F4F7FB] mb-4">
            Get in touch.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Contact Form */}
          <div ref={formRef}>
            <div className="glass-panel p-6 md:p-8">
              {submitted ? (
                <div className="text-center py-8">
                  <div className="w-16 h-16 rounded-full bg-[#27F3A8]/20 flex items-center justify-center mx-auto mb-4">
                    <Send className="w-8 h-8 text-[#27F3A8]" />
                  </div>
                  <h3 className="text-xl font-semibold text-[#F4F7FB] mb-2">
                    Message sent!
                  </h3>
                  <p className="text-[#A9B3C2]">
                    We'll get back to you within 24 hours.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="micro-label block mb-2">NAME</label>
                    <Input
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="Your name"
                      required
                      className="bg-white/5 border-white/10 text-[#F4F7FB] placeholder:text-[#A9B3C2]/50"
                    />
                  </div>
                  <div>
                    <label className="micro-label block mb-2">EMAIL</label>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="you@company.com"
                      required
                      className="bg-white/5 border-white/10 text-[#F4F7FB] placeholder:text-[#A9B3C2]/50"
                    />
                  </div>
                  <div>
                    <label className="micro-label block mb-2">MESSAGE</label>
                    <Textarea
                      value={formData.message}
                      onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                      placeholder="How can we help?"
                      required
                      rows={4}
                      className="bg-white/5 border-white/10 text-[#F4F7FB] placeholder:text-[#A9B3C2]/50 resize-none"
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full bg-[#27D3F3] text-[#0B0F17] hover:bg-[#27D3F3]/90"
                  >
                    {isSubmitting ? 'Sending...' : 'Send message'}
                    <Send className="ml-2 w-4 h-4" />
                  </Button>
                </form>
              )}
            </div>
          </div>

          {/* Contact Info */}
          <div ref={infoRef} className="space-y-6">
            <div className="glass-panel p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#27D3F3]/10 flex items-center justify-center">
                  <Mail className="w-5 h-5 text-[#27D3F3]" />
                </div>
                <div>
                  <span className="micro-label block">EMAIL</span>
                  <span className="text-[#F4F7FB]">support@trustsentinel.io</span>
                </div>
              </div>
            </div>
            
            <div className="glass-panel p-6">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-[#27F3A8]/10 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-[#27F3A8]" />
                </div>
                <div>
                  <span className="micro-label block">SUPPORT HOURS</span>
                  <span className="text-[#F4F7FB]">Mon–Fri 9am–6pm UTC</span>
                </div>
              </div>
            </div>
            
            {/* Trust Badge */}
            <div className="glass-panel p-6 border-[#27F3A8]/20">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-[#27F3A8]/10 flex items-center justify-center">
                  <Shield className="w-5 h-5 text-[#27F3A8]" />
                </div>
                <div>
                  <span className="text-sm text-[#F4F7FB] font-medium">Privacy-first by design</span>
                  <span className="block text-xs text-[#A9B3C2]">SOC 2 Type II certified</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-20 pt-10 border-t border-white/5">
        <div className="max-w-[980px] mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
            <div>
              <h4 className="text-sm font-semibold text-[#F4F7FB] mb-4">Product</h4>
              <ul className="space-y-2">
                <li><a href="#phishing-shield" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Phishing Shield</a></li>
                <li><a href="#deepfake-shield" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Deepfake Shield</a></li>
                <li><a href="#pricing" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Pricing</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-[#F4F7FB] mb-4">Company</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">About</a></li>
                <li><a href="#" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Blog</a></li>
                <li><a href="#" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Careers</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-[#F4F7FB] mb-4">Resources</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Documentation</a></li>
                <li><a href="#" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">API Reference</a></li>
                <li><a href="#faq" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">FAQ</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-[#F4F7FB] mb-4">Legal</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Terms of Service</a></li>
                <li><a href="#" className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors">Security</a></li>
              </ul>
            </div>
          </div>
          
          <div className="flex flex-col md:flex-row items-center justify-between py-6 border-t border-white/5">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <Shield className="w-5 h-5 text-[#27D3F3]" />
              <span className="font-mono text-sm text-[#F4F7FB]">Trust-Sentinel</span>
            </div>
            <p className="text-xs text-[#A9B3C2]">
              © 2026 Trust-Sentinel. Privacy-first by design.
            </p>
          </div>
        </div>
      </footer>
    </section>
  );
}
