import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, BarChart3, CalendarDays, Camera, ChevronDown, LogOut, Menu, Salad, Sparkles, UserRound, X } from 'lucide-react';
import { getProfileInitial } from '../utils/profile';

const navItems = [
  { id: 'home', label: 'Home', icon: Salad },
  { id: 'analyzer', label: 'Analyze food', icon: Camera },
  { id: 'daily', label: 'Nutrition journey', icon: CalendarDays },
  { id: 'results', label: 'Smart analysis', icon: BarChart3 },
];

function AccountMenu({ name, email, compact = false, onProfile, onSignOut, onOpenChange, isSigningOut }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const displayName = name?.trim() || email || 'Your account';
  const menuId = compact ? 'mobile-account-menu' : 'desktop-account-menu';

  useEffect(() => {
    if (!open) return undefined;
    const closeOnOutsidePointer = (event) => {
      if (!menuRef.current?.contains(event.target)) setOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      menuRef.current?.querySelector('button')?.focus();
    };
    document.addEventListener('pointerdown', closeOnOutsidePointer);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePointer);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [open]);

  const toggleMenu = () => {
    setOpen((isOpen) => !isOpen);
    onOpenChange?.();
  };
  const selectProfile = () => {
    setOpen(false);
    onProfile();
  };
  const signOut = () => {
    setOpen(false);
    onSignOut();
  };

  return (
    <div className={`account-menu${compact ? ' account-menu--compact' : ''}`} ref={menuRef}>
      <button
        type="button"
        className="account-menu-trigger"
        onClick={toggleMenu}
        aria-label={`Account menu for ${displayName}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
      >
        <span className="account-avatar" aria-hidden="true">{getProfileInitial(name, email)}</span>
        {!compact && <span className="account-display-name">{displayName}</span>}
        <ChevronDown size={14} aria-hidden="true" />
      </button>
      {open && <AccountMenuPopover
        id={menuId}
        name={displayName}
        email={email && name?.trim() ? email : ''}
        initial={getProfileInitial(name, email)}
        onProfile={selectProfile}
        onSignOut={signOut}
        isSigningOut={isSigningOut}
      />}
    </div>
  );
}

export function AccountMenuPopover({ id, name, email, initial, onProfile, onSignOut, isSigningOut = false }) {
  return (
    <div className="account-menu-popover glass-surface" id={id} role="menu" aria-label="Account">
      <div className="account-menu-identity">
        <span className="account-avatar account-avatar--menu" aria-hidden="true">{initial}</span>
        <span><strong>{name}</strong>{email && <small>{email}</small>}</span>
      </div>
      <button type="button" role="menuitem" onClick={onProfile}>
        <UserRound size={16} /><span>My Profile</span>
      </button>
      <button type="button" role="menuitem" onClick={onSignOut} disabled={isSigningOut}>
        <LogOut size={16} /><span>{isSigningOut ? 'Signing out…' : 'Sign Out'}</span>
      </button>
    </div>
  );
}

export default function Navbar({
  activeTab,
  setActiveTab,
  onSignOut,
  demoMode,
  isSigningOut = false,
  authUser = null,
  profileName = '',
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
            {demoMode && <span className="demo-mode-badge">Demo mode</span>}
            {authUser ? (
              <AccountMenu
                name={profileName}
                email={authUser.email}
                onProfile={() => navigate('profile')}
                onSignOut={onSignOut}
                isSigningOut={isSigningOut}
              />
            ) : (
              <>
                <button className={`profile-shortcut${activeTab === 'profile' ? ' is-active' : ''}`} onClick={() => navigate('profile')} aria-label="Profile and goals" aria-current={activeTab === 'profile' ? 'page' : undefined}>
                  <UserRound size={16} />
                  <span>Profile</span>
                </button>
                <button className="profile-shortcut" type="button" onClick={onSignOut} disabled={isSigningOut} aria-label={demoMode ? 'Exit demo' : 'Sign out'}>
                  <LogOut size={15} />
                  <span>{isSigningOut ? 'Signing out…' : demoMode ? 'Exit demo' : 'Sign out'}</span>
                </button>
              </>
            )}
            <button className="nav-cta" onClick={() => navigate('analyzer')}>
              <Sparkles size={15} />
              <span>Try NutriAI</span>
              <ArrowUpRight size={14} />
            </button>
          </div>

          {authUser && (
            <div className="mobile-account">
              <AccountMenu
                name={profileName}
                email={authUser.email}
                compact
                onOpenChange={() => setMobileOpen(false)}
                onProfile={() => navigate('profile')}
                onSignOut={onSignOut}
                isSigningOut={isSigningOut}
              />
            </div>
          )}

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
              {demoMode && <span className="demo-mode-badge demo-mode-badge--mobile">Demo mode · sample data only</span>}
              {!authUser && (
                <>
                  <button className={`nav-link nav-link--mobile${activeTab === 'profile' ? ' is-active' : ''}`} onClick={() => navigate('profile')} aria-current={activeTab === 'profile' ? 'page' : undefined}>
                    <UserRound size={16} /><span>Profile &amp; goals</span>
                  </button>
                  <button className="nav-link nav-link--mobile" type="button" onClick={onSignOut} disabled={isSigningOut}>
                    <LogOut size={16} /><span>{isSigningOut ? 'Signing out…' : demoMode ? 'Exit demo' : 'Sign out'}</span>
                  </button>
                </>
              )}
              <button className="mobile-nav-cta" onClick={() => navigate('analyzer')}><Camera size={16} /> Analyze a meal <ArrowUpRight size={15} /></button>
            </motion.nav>
          )}
        </AnimatePresence>
      </div>
    </header>
  );
}
