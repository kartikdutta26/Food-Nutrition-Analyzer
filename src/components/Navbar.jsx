import React, { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, BarChart3, CalendarDays, Camera, LogOut, Menu, Salad, Sparkles, UserRound, X } from 'lucide-react';

const navItems = [
  { id: 'home', label: 'Home', icon: Salad },
  { id: 'analyzer', label: 'Analyze food', icon: Camera },
  { id: 'daily', label: 'Nutrition journey', icon: CalendarDays },
  { id: 'results', label: 'Analysis results', icon: BarChart3 },
];

export default function Navbar({
  activeTab,
  setActiveTab,
  authUser = null,
  authLoading = false,
  isSigningOut = false,
  onOpenAuth,
  onLogout,
}) {
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
            {authLoading ? (
              <span role="status" className="max-w-32 truncate text-[10px] font-bold text-slate-500">Checking account…</span>
            ) : authUser ? (
              <>
                <span className="max-w-32 truncate text-[10px] font-bold text-teal-900" title={authUser.user_metadata?.full_name || authUser.email}>
                  {authUser.user_metadata?.full_name || authUser.email}
                </span>
                <button type="button" className="profile-shortcut" onClick={onLogout} disabled={isSigningOut}>
                  <LogOut size={15} />
                  <span>{isSigningOut ? 'Signing out…' : 'Sign out'}</span>
                </button>
              </>
            ) : (
              <button type="button" className="profile-shortcut" onClick={() => onOpenAuth?.('login')}>
                <UserRound size={15} />
                <span>Sign in</span>
              </button>
            )}
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
              {authLoading ? (
                <p role="status" className="px-3 py-2 text-xs font-semibold text-slate-500">Checking account…</p>
              ) : authUser ? (
                <div className="flex items-center justify-between gap-3 px-3 py-2">
                  <span className="min-w-0 truncate text-xs font-bold text-teal-900">{authUser.user_metadata?.full_name || authUser.email}</span>
                  <button type="button" onClick={() => { onLogout?.(); setMobileOpen(false); }} disabled={isSigningOut} className="inline-flex shrink-0 items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-rose-700 disabled:opacity-60">
                    <LogOut size={14} /> {isSigningOut ? 'Signing out…' : 'Sign out'}
                  </button>
                </div>
              ) : (
                <button type="button" className="nav-link nav-link--mobile" onClick={() => { onOpenAuth?.('login'); setMobileOpen(false); }}>
                  <UserRound size={16} /><span>Sign in / Create account</span>
                </button>
              )}
              <button className="mobile-nav-cta" onClick={() => navigate('analyzer')}><Camera size={16} /> Analyze a meal <ArrowUpRight size={15} /></button>
            </motion.nav>
          )}
        </AnimatePresence>
      </div>
    </header>
  );
}
