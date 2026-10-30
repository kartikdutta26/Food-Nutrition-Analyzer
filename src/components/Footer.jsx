import React from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Camera,
  Heart,
  House,
  Leaf,
  Salad,
  Smile,
  Sparkles,
  UserRound,
} from 'lucide-react';

const links = [
  { id: 'home', label: 'Home', icon: House },
  { id: 'analyzer', label: 'Analyze food', icon: Camera },
  { id: 'daily', label: 'Nutrition journey', icon: CalendarDays },
  { id: 'results', label: 'Smart analysis', icon: Sparkles },
  { id: 'profile', label: 'Profile & goals', icon: UserRound },
];

const highlights = [
  { label: 'Better choices', icon: Sparkles, tone: 'mint' },
  { label: 'Happier you', icon: Smile, tone: 'peach' },
  { label: 'Healthier tomorrow', icon: Leaf, tone: 'mint' },
];

export default function Footer({ setActiveTab }) {
  return (
    <footer className="site-footer">
      <div className="landing-container footer-main">
        <div className="footer-brand">
          <button className="brand-lockup" type="button" onClick={() => setActiveTab('home')} aria-label="NutriAI home">
            <span className="brand-mark"><Salad size={20} /></span>
            <span className="brand-name">Nutri<span>AI</span><small>INTELLIGENT NUTRITION</small></span>
          </button>
          <p>Your food. Your goals. One intelligent nutrition agent.</p>
          <span className="footer-signoff"><Heart size={13} /> Made for everyday wellbeing</span>
          <ul className="footer-highlights" aria-label="Wellbeing highlights">
            {highlights.map(({ label, icon: Icon, tone }) => (
              <li className="footer-highlight" key={label}>
                <span className={`footer-highlight-icon footer-highlight-icon--${tone}`}><Icon size={12} /></span>
                {label}
              </li>
            ))}
          </ul>
        </div>

        <nav className="footer-explore" aria-label="Explore">
          <h2>Explore</h2>
          <ul className="footer-links">
            {links.map(({ id, label, icon: Icon }) => (
              <li key={id}>
                <button type="button" onClick={() => setActiveTab(id)}>
                  <Icon className="footer-link-icon" size={14} aria-hidden="true" />
                  <span>{label}</span>
                  <ArrowUpRight className="footer-link-arrow" size={13} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="footer-cta-box">
          <img className="footer-cta-image" src="/nutriai-3d-meal-bowl.png" alt="" />
          <div className="footer-cta-content">
            <span className="footer-cta-icon"><Camera size={17} /></span>
            <strong>Curious about a meal?</strong>
            <p>Start with a photo and see what's on your plate.</p>
            <button type="button" onClick={() => setActiveTab('analyzer')}>
              Try food analysis <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>

      <div className="landing-container footer-bottom">
        <span>© {new Date().getFullYear()} NutriAI</span>
        <span>Nutrition insights to support your everyday choices.</span>
      </div>
    </footer>
  );
}
