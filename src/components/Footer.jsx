import React from 'react';
import { ArrowUpRight, Camera, Heart, Salad } from 'lucide-react';

const links = [
  { id: 'home', label: 'Home' },
  { id: 'analyzer', label: 'Analyze food' },
  { id: 'daily', label: 'Nutrition journey' },
  { id: 'results', label: 'Smart analysis' },
  { id: 'profile', label: 'Profile & goals' },
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
        </div>

        <div className="footer-links-wrap">
          <div>
            <h2>Explore</h2>
            <ul className="footer-links">
              {links.map(({ id, label }) => <li key={id}><button onClick={() => setActiveTab(id)}>{label}<ArrowUpRight size={13} /></button></li>)}
            </ul>
          </div>
          <div className="footer-cta-box">
            <span className="footer-cta-icon"><Camera size={17} /></span>
            <strong>Curious about a meal?</strong>
            <p>Start with a photo and see what’s on your plate.</p>
            <button onClick={() => setActiveTab('analyzer')}>Try food analysis <ArrowUpRight size={14} /></button>
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
