import React, { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, BarChart3, CalendarDays, Camera, Menu, Salad, Sparkles, UserRound, X } from 'lucide-react';

const navItems = [
  { id: 'home', label: 'Home', icon: Salad },
  { id: 'analyzer', label: 'Analyze food', icon: Camera },
  { id: 'daily', label: 'Nutrition journey', icon: CalendarDays },
  { id: 'results', label: 'Smart analysis', icon: BarChart3 },
];

export default function Navbar({ activeTab, setActiveTab }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const reducedMotion = useReducedMotion();

  const navigate = (tab) => {
    setActiveTab(tab);
    setMobileOpen(false);
  };

  const renderItems = (mobile = false) => navItems.map(({ id, label, icon: Icon }) => {
    const active = activeTab === id;
    return (
      <button
        key={id}
        type="button"
        onClick={() => navigate(id)}
        aria-current={active ? 'page' : undefined}
        className={`nav-link${active ? ' is-active' : ''}${mobile ? ' nav-link--mobile' : ''}`}
      >
        <Icon size={16} strokeWidth={1.8} />
        <span>{label}</span>
      </button>
    );
  });

  return (
    <header className="site-header">
      <div className="nav-frame">
        <div className="nav-bar glass-surface">
          <button className="brand-lockup" type="button" onClick={() => navigate('home')} aria-label="NutriAI home">
            <span className="brand-mark"><Salad size={21} strokeWidth={1.8} /></span>
            <span className="brand-name">Nutri<span>AI</span><small>INTELLIGENT NUTRITION</small></span>
          </button>

          <nav className="desktop-nav" aria-label="Main navigation">
            {renderItems()}
          </nav>

          <div className="nav-actions">
            <button className={`profile-shortcut${activeTab === 'profile' ? ' is-active' : ''}`} onClick={() => navigate('profile')} aria-label="Profile and goals" aria-current={activeTab === 'profile' ? 'page' : undefined}>
              <UserRound size={16} />
              <span>Profile</span>
            </button>
            <button className="nav-cta" onClick={() => navigate('analyzer')}>
              <Sparkles size={15} />
              <span>Try NutriAI</span>
              <ArrowUpRight size={14} />
            </button>
          </div>

          <button
            className="mobile-menu-toggle"
            type="button"
            onClick={() => setMobileOpen((open) => !open)}
            aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileOpen}
            aria-controls="mobile-navigation"
          >
            {mobileOpen ? <X size={21} /> : <Menu size={21} />}
          </button>
        </div>

        <AnimatePresence>
          {mobileOpen && (
            <motion.nav
              id="mobile-navigation"
              className="mobile-nav glass-surface"
              aria-label="Mobile navigation"
              initial={reducedMotion ? false : { opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reducedMotion ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {renderItems(true)}
              <button className={`nav-link nav-link--mobile${activeTab === 'profile' ? ' is-active' : ''}`} onClick={() => navigate('profile')} aria-current={activeTab === 'profile' ? 'page' : undefined}>
                <UserRound size={16} /><span>Profile &amp; goals</span>
              </button>
              <button className="mobile-nav-cta" onClick={() => navigate('analyzer')}><Camera size={16} /> Analyze a meal <ArrowUpRight size={15} /></button>
            </motion.nav>
          )}
        </AnimatePresence>
      </div>
    </header>
  );
}
