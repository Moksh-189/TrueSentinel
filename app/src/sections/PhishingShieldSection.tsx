import { useRef, useLayoutEffect, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Link2, AlertTriangle, CheckCircle, Shield, ExternalLink, Ban, Plus, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

gsap.registerPlugin(ScrollTrigger);

export function PhishingShieldSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLDivElement>(null);
  const mockupRef = useRef<HTMLDivElement>(null);

  const [url, setUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<'clean' | 'suspicious' | 'malicious' | null>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const bg = bgRef.current;
    const headline = headlineRef.current;
    const mockup = mockupRef.current;

    if (!section || !bg || !headline || !mockup) return;

    const ctx = gsap.context(() => {
      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: 'top top',
          end: '+=140%',
          pin: true,
          scrub: 0.7,
        },
      });

      // Background entrance
      scrollTl.fromTo(
        bg,
        { scale: 1.14, opacity: 0.7 },
        { scale: 1, opacity: 1, ease: 'none' },
        0
      );
      scrollTl.fromTo(
        bg,
        { scale: 1 },
        { scale: 1.12, opacity: 0.3, ease: 'none' },
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

      // Mockup entrance from right with 3D rotation
      scrollTl.fromTo(
        mockup,
        { x: '55vw', rotateY: 18, opacity: 0 },
        { x: 0, rotateY: 0, opacity: 1, ease: 'power2.out' },
        0.06
      );
      scrollTl.fromTo(
        mockup,
        { x: 0, rotateY: 0, opacity: 1 },
        { x: '18vw', rotateY: -10, opacity: 0, ease: 'power2.in' },
        0.7
      );
    }, section);

    return () => ctx.revert();
  }, []);

  const handleScan = async () => {
    if (!url) return;
    setIsScanning(true);
    setScanResult(null);

    try {
      // Call the TrustSentinel backend API
      const response = await fetch(`/check-trust?url=${encodeURIComponent(url)}`);

      if (!response.ok) {
        throw new Error('API request failed');
      }

      const data = await response.json();

      // Map API response to UI states
      if (data.status === 'danger') {
        // High confidence danger = malicious, lower = suspicious
        setScanResult(data.confidence >= 0.8 ? 'malicious' : 'suspicious');
      } else {
        setScanResult('clean');
      }
    } catch (error) {
      console.error('Error scanning URL:', error);
      // Fallback to pattern-based detection if API is unavailable
      if (url.includes('suspicious') || url.includes('phish') || url.includes('malware')) {
        setScanResult('malicious');
      } else if (url.includes('unknown')) {
        setScanResult('suspicious');
      } else {
        setScanResult('clean');
      }
    } finally {
      setIsScanning(false);
    }
  };

  const getRiskScore = () => {
    switch (scanResult) {
      case 'malicious': return 92;
      case 'suspicious': return 45;
      case 'clean': return 8;
      default: return 0;
    }
  };

  const getRiskColor = () => {
    switch (scanResult) {
      case 'malicious': return '#FF4D6D';
      case 'suspicious': return '#F3A827';
      case 'clean': return '#27F3A8';
      default: return '#27D3F3';
    }
  };

  return (
    <section
      ref={sectionRef}
      id="phishing-shield"
      className="section-pinned z-30"
    >
      {/* Background Image */}
      <div
        ref={bgRef}
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: 'url(/images/server_cables.jpg)',
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
        <span className="micro-label block mb-4 text-[#27D3F3]">PHISHING SHIELD</span>
        <h2 className="text-[36px] md:text-[48px] lg:text-[56px] font-bold text-[#F4F7FB] leading-[1.1] mb-6">
          One click. Full context.
        </h2>
        <p className="text-base md:text-lg text-[#A9B3C2] leading-relaxed">
          Paste a link. Get an instant risk score, source trace, and recommended action.
        </p>
      </div>

      {/* Right UI Mockup */}
      <div
        ref={mockupRef}
        className="absolute right-[6vw] top-[16vh] w-[40vw] min-w-[340px] max-w-[480px] z-[6]"
        style={{ perspective: '1000px' }}
      >
        <div className="glass-panel-accent p-6">
          {/* URL Input */}
          <div className="mb-6">
            <label className="micro-label block mb-2">TARGET URL</label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#A9B3C2]" />
                <Input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="pl-10 bg-white/5 border-white/10 text-[#F4F7FB] placeholder:text-[#A9B3C2]/50"
                />
              </div>
              <Button
                onClick={handleScan}
                disabled={isScanning || !url}
                className="bg-[#27D3F3] text-[#0B0F17] hover:bg-[#27D3F3]/90"
              >
                {isScanning ? 'Scanning...' : 'Scan'}
              </Button>
            </div>
          </div>

          {/* Risk Score */}
          <div className="mb-6">
            <label className="micro-label block mb-3">RISK SCORE</label>
            <div className="flex items-center gap-4">
              <div className="relative w-20 h-20">
                <svg className="w-full h-full -rotate-90">
                  <circle
                    cx="40"
                    cy="40"
                    r="36"
                    fill="none"
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="6"
                  />
                  <circle
                    cx="40"
                    cy="40"
                    r="36"
                    fill="none"
                    stroke={getRiskColor()}
                    strokeWidth="6"
                    strokeLinecap="round"
                    strokeDasharray={`${getRiskScore() * 2.26} 226`}
                    className="transition-all duration-500"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xl font-mono font-bold" style={{ color: getRiskColor() }}>
                    {getRiskScore()}
                  </span>
                </div>
              </div>
              <div>
                {scanResult === 'malicious' && (
                  <div className="flex items-center gap-2 text-[#FF4D6D]">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="font-medium">High Risk Detected</span>
                  </div>
                )}
                {scanResult === 'suspicious' && (
                  <div className="flex items-center gap-2 text-[#F3A827]">
                    <Shield className="w-5 h-5" />
                    <span className="font-medium">Suspicious Patterns</span>
                  </div>
                )}
                {scanResult === 'clean' && (
                  <div className="flex items-center gap-2 text-[#27F3A8]">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">Clean</span>
                  </div>
                )}
                {!scanResult && (
                  <span className="text-[#A9B3C2]">Enter URL to analyze</span>
                )}
              </div>
            </div>
          </div>

          {/* Sources */}
          <div className="mb-6">
            <label className="micro-label block mb-3">SOURCES</label>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.03]">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-[#27D3F3]" />
                  <span className="text-sm text-[#F4F7FB]">URLHaus Database</span>
                </div>
                <ExternalLink className="w-3 h-3 text-[#A9B3C2]" />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.03]">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-[#27F3A8]" />
                  <span className="text-sm text-[#F4F7FB]">PhishTank Feed</span>
                </div>
                <ExternalLink className="w-3 h-3 text-[#A9B3C2]" />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1 border-[#FF4D6D]/30 text-[#FF4D6D] hover:bg-[#FF4D6D]/10"
              disabled={!scanResult}
            >
              <Ban className="w-4 h-4 mr-2" />
              Block Domain
            </Button>
            <Button
              variant="outline"
              className="flex-1 border-[#27F3A8]/30 text-[#27F3A8] hover:bg-[#27F3A8]/10"
              disabled={!scanResult}
            >
              <Plus className="w-4 h-4 mr-2" />
              Allowlist
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
