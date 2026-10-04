import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Brain,
  Camera,
  Check,
  CheckCircle2,
  Clock3,
  Flame,
  Heart,
  Leaf,
  Salad,
  Sparkles,
  Target,
} from 'lucide-react';

function Reveal({ children, className = '', delay = 0 }) {
  const reducedMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reducedMotion ? false : { opacity: 0, y: 20 }}
      whileInView={reducedMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.16 }}
      transition={{ duration: 0.65, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

const features = [
  {
    icon: Camera,
    title: 'Analyze your food',
    text: 'Add a meal photo and explore its estimated nutrition at a glance.',
    action: 'Try the analyzer',
    tab: 'analyzer',
    tint: 'peach',
  },
  {
    icon: BarChart3,
    title: 'Track daily nutrition',
    text: 'Keep calories and macros in view as you build your everyday routine.',
    action: 'View your journey',
    tab: 'daily',
    tint: 'aqua',
  },
  {
    icon: Target,
    title: 'Set personal goals',
    text: 'Shape nutrition targets around the goals and habits that matter to you.',
    action: 'Set your goals',
    tab: 'profile',
    tint: 'peach',
  },
  {
    icon: Brain,
    title: 'Understand your meals',
    text: 'Review meal insights and practical ideas for finding a better balance.',
    action: 'Explore smart analysis',
    tab: 'results',
    tint: 'aqua',
  },
];

const steps = [
  { number: '01', title: 'Add a meal', text: 'Upload a photo, use your camera, or choose a meal by name.', icon: Camera },
  { number: '02', title: 'Explore the estimate', text: 'See a clear breakdown of calories, macros, and key nutrients.', icon: Sparkles },
  { number: '03', title: 'Make it yours', text: 'Log a meal and follow your daily goals as they take shape.', icon: CheckCircle2 },
];

export default function HeroLanding({ onNavigateToAnalyzer, onNavigateToDaily, setActiveTab }) {
  const goTo = (tab) => setActiveTab?.(tab);

  return (
    <div className="landing-page">
      <section className="hero-section" aria-labelledby="hero-title">
        <div className="hero-orbit hero-orbit--aqua" aria-hidden="true" />
        <div className="hero-orbit hero-orbit--peach" aria-hidden="true" />
        <div className="landing-container hero-layout">
          <div className="hero-copy">
            <motion.div
              className="eyebrow hero-eyebrow"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <span className="eyebrow-spark"><Sparkles size={14} /></span>
              AI powered nutrition agent
            </motion.div>

            <motion.h1
              id="hero-title"
              className="hero-title"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
            >
              Nutri<span>AI</span>
            </motion.h1>

            <motion.p
              className="hero-subtitle"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.18 }}
            >
              Your food. Your goals.<br />
              <span>One intelligent nutrition agent.</span>
            </motion.p>

            <motion.p
              className="hero-description"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.26 }}
            >
              Snap your meal, understand what’s on your plate, and get personalized insights. Let AI help you decide what to eat next.
            </motion.p>

            <motion.div
              className="hero-actions"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.34 }}
            >
              <button className="button button-primary" onClick={onNavigateToAnalyzer}>
                <Camera size={18} />
                Analyze my meal
                <ArrowRight size={16} />
              </button>
              <button className="button button-glass" onClick={onNavigateToDaily}>
                <Sparkles size={16} />
                Start my nutrition journey
              </button>
            </motion.div>

            <motion.div
              className="hero-proof"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.48 }}
            >
              <div className="proof-avatars" aria-hidden="true">
                <span><Leaf size={13} /></span><span><Heart size={12} /></span><span><Salad size={13} /></span>
              </div>
              <p><strong>A little more clarity,</strong> one meal at a time</p>
            </motion.div>
          </div>

          <motion.div
            className="hero-visual"
            initial={{ opacity: 0, scale: 0.97, x: 18 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            transition={{ duration: 0.85, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="hero-image-frame">
              <img
                className="hero-food-image"
                src="/nutriai-bowl.webp"
                alt="A colorful grain bowl with avocado, chickpeas, leafy greens, tomatoes, and fresh herbs"
                fetchPriority="high"
              />
            </div>
          </motion.div>
        </div>

        <div className="landing-container hero-note-row">
          <span><CheckCircle2 size={16} /> Simple meal insights</span>
          <span><CheckCircle2 size={16} /> Personal daily goals</span>
          <span><CheckCircle2 size={16} /> Your food, your pace</span>
        </div>
      </section>

      <section className="feature-section section-space" aria-labelledby="features-title">
        <div className="landing-container">
          <Reveal className="section-heading">
            <span className="eyebrow"><span className="eyebrow-dot" /> A little support for every plate</span>
            <h2 id="features-title">What can NutriAI do for you?</h2>
            <p>Thoughtful tools to help make nutrition feel clearer and more personal.</p>
          </Reveal>

          <div className="feature-grid">
            {features.map(({ icon: Icon, title, text, action, tab, tint }, index) => (
              <Reveal key={title} delay={index * 0.08} className="feature-card-wrap">
                <button className="feature-card glass-surface" onClick={() => goTo(tab)}>
                  <span className={`feature-icon feature-icon--${tint}`}><Icon size={20} strokeWidth={1.8} /></span>
                  <span className="feature-arrow"><ArrowUpRight size={17} /></span>
                  <strong>{title}</strong>
                  <span className="feature-description">{text}</span>
                  <span className="feature-link">{action}<ArrowRight size={14} /></span>
                </button>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="how-section section-space" aria-labelledby="how-title">
        <div className="landing-container how-layout">
          <Reveal className="how-intro">
            <span className="eyebrow"><span className="eyebrow-dot" /> Simple by design</span>
            <h2 id="how-title">Good choices start with a little more insight.</h2>
            <p>From a quick photo to a steady daily routine, NutriAI helps you connect the dots without making food feel complicated.</p>
            <button className="text-link" onClick={onNavigateToAnalyzer}>Try a meal analysis <ArrowRight size={16} /></button>
          </Reveal>

          <div className="steps-list">
            {steps.map(({ number, title, text, icon: Icon }, index) => (
              <Reveal key={number} delay={index * 0.1} className="step-row">
                <span className="step-index">{number}</span>
                <span className="step-icon"><Icon size={18} /></span>
                <span className="step-copy"><strong>{title}</strong><small>{text}</small></span>
                {index < steps.length - 1 && <span className="step-connector" aria-hidden="true" />}
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="demo-section section-space" aria-labelledby="demo-title">
        <div className="landing-container demo-layout">
          <Reveal className="demo-visual-wrap">
            <div className="demo-card glass-surface">
              <div className="demo-card-top">
                <span className="demo-live-dot" /> Sample nutrition preview
                <span className="demo-tag">DEMO</span>
              </div>
              <div className="demo-meal-row">
                <img src="/nutriai-bowl.webp" alt="Sample grain bowl" loading="lazy" />
                <div><strong>Colorful grain bowl</strong><small>Illustrative example</small><span><Clock3 size={13} /> A balanced lunch idea</span></div>
              </div>
              <div className="demo-calorie-row"><span>Estimated energy</span><strong>620 <small>kcal</small></strong></div>
              <div className="macro-bars" aria-label="Illustrative macronutrient breakdown">
                <div><span>Protein <b>28 g</b></span><i><em className="macro-protein" /></i></div>
                <div><span>Carbohydrates <b>72 g</b></span><i><em className="macro-carbs" /></i></div>
                <div><span>Fat <b>22 g</b></span><i><em className="macro-fat" /></i></div>
              </div>
              <p className="demo-disclaimer">Example values shown for design preview only.</p>
            </div>
            <div className="demo-stamp"><Sparkles size={16} /><span>Clarity that<br /><strong>fits your day</strong></span></div>
          </Reveal>

          <Reveal className="demo-copy">
            <span className="eyebrow"><span className="eyebrow-dot" /> Your plate, in perspective</span>
            <h2 id="demo-title">See the whole picture, one meal at a time.</h2>
            <p>Get a simple view of meal estimates, daily progress, and practical nutrition insights in one calm, easy-to-read space.</p>
            <ul className="check-list">
              <li><CheckCircle2 size={17} /> Meal details at a glance</li>
              <li><CheckCircle2 size={17} /> Daily progress that feels motivating</li>
              <li><CheckCircle2 size={17} /> Goals shaped around your preferences</li>
            </ul>
            <button className="button button-primary" onClick={onNavigateToAnalyzer}>Explore the analyzer <ArrowRight size={16} /></button>
          </Reveal>
        </div>
      </section>

      <section className="personal-section section-space" aria-labelledby="personal-title">
        <div className="landing-container personal-layout">
          <Reveal className="personal-copy">
            <span className="eyebrow"><span className="eyebrow-dot" /> A routine that feels like yours</span>
            <h2 id="personal-title">Small, steady steps can add up.</h2>
            <p>Set a goal, notice your patterns, and keep the parts of healthy eating that work for you. Your profile and daily tracker stay connected as you go.</p>
            <div className="personal-actions">
              <button className="button button-glass" onClick={() => goTo('profile')}><Target size={16} /> Personalize your goals</button>
              <button className="text-link" onClick={onNavigateToDaily}>View daily tracker <ArrowRight size={16} /></button>
            </div>
          </Reveal>
          <Reveal className="goal-preview glass-surface" delay={0.08}>
            <div className="goal-preview-head"><span className="goal-preview-icon"><Target size={18} /></span><span><small>YOUR EVERYDAY OVERVIEW</small><strong>A steady rhythm</strong></span><span className="goal-chip">Personal</span></div>
            <div className="goal-progress"><div><span>Daily energy</span><strong>1,420 <small>/ 2,000 kcal</small></strong></div><span className="progress-track"><i /></span></div>
            <div className="goal-metrics">
              <div><span className="metric-icon metric-icon--peach"><Flame size={15} /></span><small>Protein</small><strong>78 <i>g</i></strong><span className="mini-track"><i className="mini-track--protein" /></span></div>
              <div><span className="metric-icon metric-icon--aqua"><Leaf size={15} /></span><small>Carbs</small><strong>165 <i>g</i></strong><span className="mini-track"><i className="mini-track--carbs" /></span></div>
              <div><span className="metric-icon metric-icon--peach"><Heart size={15} /></span><small>Fats</small><strong>45 <i>g</i></strong><span className="mini-track"><i className="mini-track--fats" /></span></div>
            </div>
            <div className="goal-preview-foot"><span><Check size={14} /> Your daily tracker preview</span><span>Example</span></div>
          </Reveal>
        </div>
      </section>

      <section className="closing-section">
        <div className="landing-container">
          <Reveal className="closing-card">
            <div className="closing-glow closing-glow--one" aria-hidden="true" />
            <div className="closing-glow closing-glow--two" aria-hidden="true" />
            <span className="closing-mark"><Salad size={22} /></span>
            <span className="eyebrow">A more thoughtful way to eat</span>
            <h2>Make room for feeling good.</h2>
            <p>Start with what’s on your plate today. The next step can be a small one.</p>
            <div className="closing-actions">
              <button className="button button-primary" onClick={onNavigateToAnalyzer}><Camera size={17} /> Analyze a meal <ArrowRight size={15} /></button>
              <button className="button button-glass" onClick={onNavigateToDaily}>Open daily tracker</button>
            </div>
          </Reveal>
        </div>
      </section>
    </div>
  );
}
