import { useState, useEffect } from 'react';
import { Menu, X, Shield, Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function Navigation() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check localStorage or default to dark mode (matches existing theme)
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('trustsentinel-theme');
      return saved ? saved === 'dark' : true; // Default to dark
    }
    return true;
  });

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 100);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    if (isDarkMode) {
      root.classList.add('dark');
      root.classList.remove('light');
      localStorage.setItem('trustsentinel-theme', 'dark');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
      localStorage.setItem('trustsentinel-theme', 'light');
    }
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      setIsMobileMenuOpen(false);
    }
  };

  return (
    <>
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${isScrolled
          ? 'bg-[#0B0F17]/90 backdrop-blur-xl border-b border-white/5'
          : 'bg-transparent'
          }`}
      >
        <div className="flex items-center justify-between px-6 lg:px-10 py-4">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-[#27D3F3]" />
            <span className="font-mono text-sm font-medium tracking-wider text-[#F4F7FB]">
              Trust-Sentinel
            </span>
          </div>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-8">
            <button
              onClick={() => scrollToSection('phishing-shield')}
              className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors"
            >
              Products
            </button>
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors"
            >
              Docs
            </button>
            <button
              onClick={() => scrollToSection('pricing')}
              className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors"
            >
              Pricing
            </button>
            <button
              onClick={() => scrollToSection('contact')}
              className="text-sm text-[#A9B3C2] hover:text-[#F4F7FB] transition-colors"
            >
              Contact
            </button>
          </div>

          {/* Theme Toggle & CTA Button */}
          <div className="hidden md:flex items-center gap-3">
            {/* Dark Mode Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-[#A9B3C2] hover:text-[#F4F7FB] transition-all"
              aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDarkMode ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>

            <Button
              variant="outline"
              onClick={() => scrollToSection('final-cta')}
              className="border-[#27D3F3]/50 text-[#27D3F3] hover:bg-[#27D3F3]/10 text-sm"
            >
              Get Started
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-[#F4F7FB]"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </nav>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-40 bg-[#0B0F17]/98 backdrop-blur-xl md:hidden">
          <div className="flex flex-col items-center justify-center h-full gap-8">
            <button
              onClick={() => scrollToSection('phishing-shield')}
              className="text-xl text-[#F4F7FB] hover:text-[#27D3F3] transition-colors"
            >
              Products
            </button>
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="text-xl text-[#F4F7FB] hover:text-[#27D3F3] transition-colors"
            >
              Docs
            </button>
            <button
              onClick={() => scrollToSection('pricing')}
              className="text-xl text-[#F4F7FB] hover:text-[#27D3F3] transition-colors"
            >
              Pricing
            </button>
            <button
              onClick={() => scrollToSection('contact')}
              className="text-xl text-[#F4F7FB] hover:text-[#27D3F3] transition-colors"
            >
              Contact
            </button>
            <Button
              onClick={() => scrollToSection('final-cta')}
              className="mt-4 bg-[#27D3F3] text-[#0B0F17] hover:bg-[#27D3F3]/90"
            >
              Get Started
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
