import { useRef, useLayoutEffect, useState, useEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ScanFace, Activity, AlertCircle } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

export function DeepfakeShieldSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLDivElement>(null);
  const scanCardRef = useRef<HTMLDivElement>(null);
  const waveformRef = useRef<SVGPathElement>(null);

  const [isLive, setIsLive] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [bpm, setBpm] = useState(72);
  const [waveformData, setWaveformData] = useState<number[]>([]);
  const [analysisResult, setAnalysisResult] = useState<{ score: number, message: string, status: string } | null>(null);

  // Generate realistic rPPG waveform
  useEffect(() => {
    const generateWaveform = () => {
      const points: number[] = [];
      const baseFreq = bpm / 60; // Hz
      const samples = 100;
      for (let i = 0; i < samples; i++) {
        const t = i / samples;
        // Simulate cardiac pulse with harmonics
        const pulse = Math.sin(2 * Math.PI * baseFreq * t * 3) * 0.5 +
          Math.sin(2 * Math.PI * baseFreq * t * 6) * 0.25 +
          Math.sin(2 * Math.PI * baseFreq * t * 9) * 0.125;
        // Add some noise for realism
        const noise = (Math.random() - 0.5) * 0.1;
        points.push(Math.max(-1, Math.min(1, pulse + noise)));
      }
      setWaveformData(points);
    };

    generateWaveform();
    const interval = setInterval(generateWaveform, 100);
    return () => clearInterval(interval);
  }, [bpm]);

  // Simulate BPM variation
  useEffect(() => {
    const interval = setInterval(() => {
      setBpm(prev => {
        const variation = (Math.random() - 0.5) * 4;
        return Math.max(60, Math.min(90, prev + variation));
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const bg = bgRef.current;
    const headline = headlineRef.current;
    const scanCard = scanCardRef.current;
    const waveform = waveformRef.current;

    if (!section || !bg || !headline || !scanCard) return;

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
        { scale: 1.12, opacity: 0.7 },
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

      // Scan card entrance from right
      scrollTl.fromTo(
        scanCard,
        { x: '55vw', opacity: 0 },
        { x: 0, opacity: 1, ease: 'power2.out' },
        0.06
      );
      scrollTl.fromTo(
        scanCard,
        { x: 0, opacity: 1 },
        { x: '18vw', opacity: 0, ease: 'power2.in' },
        0.7
      );

      // Waveform draw-on effect
      if (waveform) {
        const length = waveform.getTotalLength?.() || 300;
        gsap.set(waveform, { strokeDasharray: length, strokeDashoffset: length });
        scrollTl.to(
          waveform,
          { strokeDashoffset: 0, ease: 'none' },
          0.1
        );
        scrollTl.to(
          waveform,
          { opacity: 0, ease: 'power2.in' },
          0.85
        );
      }
    }, section);

    return () => ctx.revert();
  }, []);

  // Generate SVG path from waveform data
  const generatePath = () => {
    if (waveformData.length === 0) return '';
    const width = 280;
    const height = 80;
    const step = width / (waveformData.length - 1);

    return waveformData.map((y, i) => {
      const x = i * step;
      const normalizedY = height / 2 + y * (height / 2 - 10);
      return `${i === 0 ? 'M' : 'L'} ${x} ${normalizedY}`;
    }).join(' ');
  };

  return (
    <section
      ref={sectionRef}
      id="deepfake-shield"
      className="section-pinned z-40"
    >
      {/* Background Image */}
      <div
        ref={bgRef}
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: 'url(/images/face_scan.jpg)',
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
        <span className="micro-label block mb-4 text-[#27F3A8]">DEEPFAKE DETECTOR</span>
        <h2 className="text-[36px] md:text-[48px] lg:text-[56px] font-bold text-[#F4F7FB] leading-[1.1] mb-6">
          Truth Revealed.
        </h2>
        <p className="text-base md:text-lg text-[#A9B3C2] leading-relaxed">
          Advanced AI analysis to detect deepfakes, face swaps, and manipulated media in real-time.
        </p>
      </div>

      {/* Right Scan Card */}
      <div
        ref={scanCardRef}
        className="absolute right-[6vw] top-[18vh] w-[40vw] min-w-[340px] max-w-[480px] z-[6]"
      >
        <div className="glass-panel-accent p-6 relative overflow-hidden">

          {/* RESULTS VIEW */}
          {!isLive && analysisResult && !isAnalyzing ? (
            <div className="flex flex-col items-center justify-center py-8 animate-in fade-in zoom-in duration-500">
              {/* Simple Icon */}
              <div className="relative w-32 h-32 mb-6 flex items-center justify-center">
                {analysisResult.status === 'authentic' ? (
                  <div className="w-full h-full rounded-full bg-[#27F3A8]/20 flex items-center justify-center border-4 border-[#27F3A8]">
                    <svg className="w-16 h-16 text-[#27F3A8]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                ) : (
                  <div className="w-full h-full rounded-full bg-[#FF4D6D]/20 flex items-center justify-center border-4 border-[#FF4D6D]">
                    <AlertCircle className="w-16 h-16 text-[#FF4D6D]" />
                  </div>
                )}
              </div>

              <div className={`text-3xl font-bold mb-4 ${analysisResult.status === 'authentic' ? 'text-[#27F3A8]' : 'text-[#FF4D6D]'}`}>
                {analysisResult.status === 'authentic' ? 'AUTHENTIC' : 'DEEPFAKE DETECTED'}
              </div>

              <button
                onClick={() => {
                  setIsLive(true);
                  setAnalysisResult(null);
                  const fileInput = document.getElementById('image-upload') as HTMLInputElement;
                  if (fileInput) fileInput.value = '';
                }}
                className="px-6 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-all flex items-center gap-2"
              >
                <ScanFace className="w-4 h-4" />
                Scan Another
              </button>
            </div>
          ) : (
            /* SCANNER VIEW */
            <>
              {/* Video Thumbnail with Scan Effect */}
              <div className="relative mb-6 rounded-xl overflow-hidden bg-[#0B0F17]/80 aspect-video">
                {/* Corner Brackets */}
                <div className="absolute top-3 left-3 w-6 h-6 border-l-2 border-t-2 border-[#27D3F3]" />
                <div className="absolute top-3 right-3 w-6 h-6 border-r-2 border-t-2 border-[#27D3F3]" />
                <div className="absolute bottom-3 left-3 w-6 h-6 border-l-2 border-b-2 border-[#27D3F3]" />
                <div className="absolute bottom-3 right-3 w-6 h-6 border-r-2 border-b-2 border-[#27D3F3]" />

                {/* Center Content */}
                <div className="absolute inset-0 flex items-center justify-center">
                  {isAnalyzing ? (
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-16 h-16 border-4 border-[#27D3F3]/30 border-t-[#27D3F3] rounded-full animate-spin" />
                      <span className="text-[#27D3F3] font-medium animate-pulse">Analyzing Media...</span>
                    </div>
                  ) : (
                    <div className="relative">
                      <ScanFace className="w-20 h-20 text-[#27D3F3]/40" />
                      {isLive && (
                        <>
                          <div className="absolute inset-0 rounded-full border-2 border-[#27F3A8]/60 pulse-ring" />
                          <div className="absolute -inset-2 rounded-full border border-[#27F3A8]/30 pulse-ring" style={{ animationDelay: '0.5s' }} />
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Scan Line (Only when live) */}
                {isLive && !isAnalyzing && (
                  <div className="absolute inset-0 overflow-hidden">
                    <div
                      className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#27D3F3] to-transparent"
                      style={{
                        animation: 'scan-vertical 2s ease-in-out infinite',
                      }}
                    />
                  </div>
                )}

                {/* Status Badge */}
                <div className="absolute top-3 left-1/2 -translate-x-1/2">
                  <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${isLive ? 'bg-[#27F3A8]/20' : 'bg-[#27D3F3]/20'}`}>
                    {isLive ? (
                      <>
                        <div className="w-2 h-2 rounded-full bg-[#27F3A8] animate-pulse" />
                        <span className="text-xs font-medium text-[#27F3A8]">Ready to Scan</span>
                      </>
                    ) : isAnalyzing ? (
                      <>
                        <Activity className="w-3 h-3 text-[#27D3F3] animate-spin" />
                        <span className="text-xs font-medium text-[#27D3F3]">Processing</span>
                      </>
                    ) : null}
                  </div>
                </div>
              </div>

              {/* Waveform Graph */}
              <div className="mb-4">
                <div className="flex justify-between items-end mb-2">
                  <label className="micro-label block">SIGNAL ANALYSIS</label>
                  <span className="text-xs font-mono text-[#27D3F3]">{isAnalyzing ? "CAPTURING..." : "IDLE"}</span>
                </div>
                <div className="relative h-20 bg-white/[0.03] rounded-lg overflow-hidden">
                  <svg
                    className="absolute inset-0 w-full h-full"
                    viewBox="0 0 280 80"
                    preserveAspectRatio="none"
                  >
                    <defs>
                      <linearGradient id="waveGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#27F3A8" stopOpacity="0.3" />
                        <stop offset="50%" stopColor="#27F3A8" stopOpacity="1" />
                        <stop offset="100%" stopColor="#27F3A8" stopOpacity="0.3" />
                      </linearGradient>
                    </defs>
                    <path
                      ref={waveformRef}
                      d={generatePath()}
                      fill="none"
                      stroke="url(#waveGradient)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      className="waveform-pulse"
                      style={{ opacity: isLive ? 1 : 0.3 }}
                    />
                  </svg>

                  {/* Grid Lines */}
                  <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute left-1/4 top-0 bottom-0 w-px bg-white/5" />
                    <div className="absolute left-2/4 top-0 bottom-0 w-px bg-white/5" />
                    <div className="absolute left-3/4 top-0 bottom-0 w-px bg-white/5" />
                    <div className="absolute top-1/2 left-0 right-0 h-px bg-white/5" />
                  </div>
                </div>
              </div>

              {/* Upload Action Area */}
              <div className="mt-6">
                <div className="flex gap-4 w-full">
                  <input
                    type="file"
                    id="image-upload"
                    className="hidden"
                    accept="image/*,video/*"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;

                      setIsLive(false);
                      setIsAnalyzing(true);
                      setAnalysisResult(null);

                      const formData = new FormData();
                      const isVideo = file.type.startsWith('video/');
                      const endpoint = isVideo ? "/detect-deepfake-video" : "/detect-deepfake";

                      formData.append(isVideo ? "video" : "image", file);

                      try {
                        const res = await fetch(endpoint, { method: "POST", body: formData });
                        if (!res.ok) throw new Error(`Server error: ${res.status}`);

                        const data = await res.json();

                        // Set full result object
                        setAnalysisResult({
                          score: data.deepfake_score,
                          message: data.message,
                          status: data.status
                        });
                        setIsLive(false); // Ensure we stay in result mode

                      } catch (err) {
                        alert("Analysis failed: " + err);
                        setIsLive(true);
                      } finally {
                        setIsAnalyzing(false);
                      }
                    }}
                  />
                  <label
                    htmlFor="image-upload"
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-[#27D3F3] text-[#0B0F17] font-semibold cursor-pointer hover:bg-[#27D3F3]/90 transition-all shadow-[0_0_20px_rgba(39,211,243,0.3)] hover:shadow-[0_0_30px_rgba(39,211,243,0.5)]"
                  >
                    <ScanFace className="w-5 h-5" />
                    <span>Upload Media for Analysis</span>
                  </label>
                </div>
                <p className="text-center text-xs text-[#A9B3C2] mt-3">
                  Supported formats: JPG, PNG, MP4, MOV
                </p>
              </div>
            </>
          )}

        </div>
      </div>

      <div className="hidden">
        {/* Preload icons or resources if needed */}
      </div>

      <style>{`
        @keyframes scan-vertical {
          0%, 100% { top: 0; opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
      `}</style>
    </section>
  );
}
