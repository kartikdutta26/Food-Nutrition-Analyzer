import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Camera,
  Check,
  CheckCircle2,
  Clock3,
  Flame,
  Leaf,
  ScanLine,
  Salad,
  Sparkles,
  Target,
  Wheat,
} from 'lucide-react';

const recognitionImage = '/nutriai-feature-recognition.png';
const scanningImage = '/nutriai-feature-scan.png';
const recommendationImage = '/nutriai-bowl.webp';

function Reveal({ children, className = '', delay = 0, direction = 'up' }) {
  const reducedMotion = useReducedMotion();
  const offset = direction === 'left' ? { x: -22 } : direction === 'right' ? { x: 22 } : { y: 16 };

  return (
    <motion.div
      className={className}
      initial={reducedMotion ? false : { opacity: 0, ...offset }}
      whileInView={reducedMotion ? undefined : { opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, amount: 0.12 }}
      transition={{ duration: 0.46, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

const nutrition = [
  { name: 'Calories', value: '520', unit: 'kcal', progress: 68, icon: Flame },
  { name: 'Protein', value: '24', unit: 'g', progress: 57, icon: Target },
  { name: 'Carbs', value: '58', unit: 'g', progress: 62, icon: Wheat },
  { name: 'Fats', value: '21', unit: 'g', progress: 43, icon: Salad },
  { name: 'Fiber', value: '12', unit: 'g', progress: 76, icon: Leaf },
];

const week = [
  { day: 'M', amount: 45 },
  { day: 'T', amount: 72 },
  { day: 'W', amount: 58 },
  { day: 'T', amount: 88 },
  { day: 'F', amount: 67 },
  { day: 'S', amount: 96 },
  { day: 'S', amount: 61 },
];

export default function HeroLanding({ onNavigateToAnalyzer, onNavigateToDaily, setActiveTab }) {
  const reducedMotion = useReducedMotion();
  const goTo = (tab) => setActiveTab?.(tab);

  return (
    <div className="landing-page">
      <section className="hero-section" aria-labelledby="hero-title">
        <div className="hero-container hero-layout">
          <div className="hero-copy">
            <motion.div
              className="eyebrow hero-eyebrow"
              initial={reducedMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55 }}
            >
              <span className="eyebrow-spark"><Sparkles size={14} /></span>
              AI powered nutrition agent
            </motion.div>

            <h2 className="hero-brand">Nutri<span>AI</span></h2>
            <motion.h1
              id="hero-title"
              className="hero-title"
              initial={reducedMotion ? false : { opacity: 0, y: 20, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ duration: 0.75, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
            >
              Your food.<br /><span>Your goals.</span>
            </motion.h1>

            <motion.p
              className="hero-subtitle"
              initial={reducedMotion ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, delay: 0.18 }}
            >
              One intelligent nutrition agent.
            </motion.p>

            <motion.p
              className="hero-description"
              initial={reducedMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.26 }}
            >
              Snap your meal, understand what’s on your plate, and get personalized insights.
              Let AI help you decide what to eat next.
            </motion.p>

            <motion.div
              className="hero-actions"
              initial={reducedMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.34 }}
            >
              <button className="button button-primary" type="button" onClick={onNavigateToAnalyzer}>
                <Camera size={17} /> Analyze my meal <ArrowRight size={16} />
              </button>
              <button className="button button-glass" type="button" onClick={onNavigateToDaily}>
                Start my nutrition journey
              </button>
            </motion.div>

            <motion.div
              className="hero-proof"
              initial={reducedMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.52 }}
            >
              <span className="proof-icon"><Check size={14} /></span>
              Thoughtful insights, one meal at a time
            </motion.div>
          </div>

        </div>

        <a className="hero-scroll" href="#recognition"><span>Discover NutriAI</span><ArrowDown size={14} /></a>
      </section>

      <section className="story-section recognition-section" id="recognition" aria-labelledby="recognition-title">
        <div className="story-container recognition-layout">
          <Reveal className="recognition-visual" direction="left">
            <div className="story-photo story-photo--recognition">
              <img src={recognitionImage} alt="Green curry bowl with rice, sliced peppers, and fresh herbs" loading="lazy" />
              <span className="photo-index">01 <i /> FOOD, UNDERSTOOD</span>
              <div className="ingredient-tag ingredient-tag--one"><span /> Fresh greens</div>
              <div className="ingredient-tag ingredient-tag--two"><span /> Jasmine rice</div>
              <div className="ingredient-tag ingredient-tag--three"><span /> Green peppers</div>
            </div>
            <div className="recognition-note glass-surface">
              <span className="recognition-note-icon"><Sparkles size={16} /></span>
              <span><small>THE LITTLE DETAILS MATTER</small><strong>More than just a meal.</strong></span>
            </div>
          </Reveal>

          <Reveal className="story-copy recognition-copy" direction="right" delay={0.08}>
            <span className="eyebrow"><span className="eyebrow-dot" /> A clearer view of your plate</span>
            <h2 id="recognition-title">Your food,<br /><span>understood by AI.</span></h2>
            <p>Every meal has a story. NutriAI helps you see what’s on your plate and turns a simple photo into helpful, easy-to-understand nutrition insights.</p>
            <div className="recognition-list">
              <span><CheckCircle2 size={17} /> Recognize ingredients at a glance</span>
              <span><CheckCircle2 size={17} /> Get a thoughtful nutrition overview</span>
              <span><CheckCircle2 size={17} /> Keep your own goals in view</span>
            </div>
            <button className="text-link" type="button" onClick={onNavigateToAnalyzer}>See how meal analysis works <ArrowRight size={16} /></button>
          </Reveal>
        </div>
      </section>

      <section className="story-section scan-section" aria-labelledby="scan-title">
        <div className="story-container scan-layout">
          <Reveal className="scan-visual-wrap" direction="left">
            <div className="scan-glass-card glass-surface">
              <div className="scan-card-heading"><span><span className="status-dot" /> NUTRIAI FOOD SCAN</span><span className="scan-card-step">01 <i /> 03</span></div>
              <div className="scan-image">
                <img src={scanningImage} alt="A colorful spread of fresh vegetables, berries, grains, and protein-rich foods" loading="lazy" />
                <span className="scan-target scan-target--avocado" aria-hidden="true" />
                <span className="scan-target scan-target--tomatoes" aria-hidden="true" />
                <span className="scan-target scan-target--chickpeas" aria-hidden="true" />
                <span className="scan-label scan-label--avocado">Avocado</span>
                <span className="scan-label scan-label--tomatoes">Blueberries</span>
                <span className="scan-label scan-label--chickpeas">Chickpeas</span>
                <span className="scan-beam" aria-hidden="true" />
                <span className="scan-image-vignette" aria-hidden="true" />
                <div className="scan-result"><Sparkles size={14} /><span><small>YOUR MEAL AT A GLANCE</small><strong>Colorful grain bowl</strong></span><CheckCircle2 size={17} /></div>
              </div>
              <div className="scan-card-foot"><span>Meal recognition</span><span><span className="scan-progress"><i /></span> Thoughtfully estimated</span></div>
            </div>
            <span className="scan-decor" aria-hidden="true"><Sparkles size={20} /></span>
          </Reveal>

          <Reveal className="story-copy scan-copy" direction="right" delay={0.08}>
            <span className="eyebrow"><span className="eyebrow-dot" /> From a photo to the full picture</span>
            <h2 id="scan-title">From a photo to<br /><span>nutrition insights.</span></h2>
            <p>A gentle scan brings the pieces together: recognize a meal, explore its estimated nutrients, and decide what feels right for you.</p>
            <div className="scan-fact"><span className="scan-fact-icon"><ScanLine size={18} /></span><span><strong>One photo, a little more context</strong><small>Clear estimates, presented with care.</small></span></div>
            <button className="text-link" type="button" onClick={onNavigateToAnalyzer}>Try a meal scan <ArrowRight size={16} /></button>
          </Reveal>
        </div>
      </section>

      <section className="story-section nutrition-section" aria-labelledby="nutrition-title">
        <div className="story-container">
          <Reveal className="nutrition-heading">
            <span className="eyebrow"><span className="eyebrow-dot" /> A little context, made simple</span>
            <h2 id="nutrition-title">Know what’s<br /><span>on your plate.</span></h2>
            <p>A clear snapshot of the nutrients that make up a meal, without getting lost in the numbers.</p>
          </Reveal>
          <div className="nutrition-grid">
            {nutrition.map(({ name, value, unit, progress, icon: Icon }, index) => (
              <Reveal className={`nutrition-card nutrition-card--${index + 1} glass-surface`} key={name} delay={index * 0.04} direction={index % 2 === 0 ? 'up' : 'right'}>
                <span className="nutrition-icon"><Icon size={17} /></span>
                <span className="nutrition-label">{name}</span>
                <strong className="nutrition-value">{value}<small> {unit}</small></strong>
                <span className="nutrition-track"><i style={{ '--progress': `${progress}%` }} /></span>
              </Reveal>
            ))}
          </div>
          <p className="illustrative-note"><Sparkles size={13} /> Illustrative nutrition preview only — not a record of your meals.</p>
        </div>
      </section>

      <section className="story-section recommendation-section" aria-labelledby="recommendation-title">
        <div className="story-container recommendation-layout">
          <Reveal className="recommendation-image" direction="left">
            <img src={recommendationImage} alt="Fresh avocado and chickpea grain bowl for a balanced meal idea" loading="lazy" />
            <span className="recommendation-image-label"><Leaf size={14} /> A balanced lunch idea</span>
          </Reveal>

          <Reveal className="story-copy recommendation-copy" direction="right" delay={0.08}>
            <span className="eyebrow"><span className="eyebrow-dot" /> Thoughtful ideas, your way</span>
            <h2 id="recommendation-title">Nutrition that<br /><span>understands your goals.</span></h2>
            <p>Small, practical suggestions can make a routine feel more personal. Explore a meal idea and see how it might fit into your day.</p>
            <div className="recommendation-card glass-surface">
              <div className="recommendation-card-head"><span className="recommendation-spark"><Sparkles size={15} /></span><span><small>AN IDEA TO INSPIRE YOU</small><strong>Colorful chickpea bowl</strong></span><ArrowUpRight size={17} /></div>
              <p>A mix of satisfying ingredients and fresh greens makes this a lovely starting point for a balanced lunch.</p>
              <div className="recommendation-meta"><span><Clock3 size={14} /> An easy lunch idea</span><span><Target size={14} /> Personalizable</span></div>
              <span className="recommendation-disclaimer">Illustrative suggestion — not generated from your personal health data.</span>
            </div>
            <button className="text-link" type="button" onClick={() => goTo('profile')}>Make it personal <ArrowRight size={16} /></button>
          </Reveal>
        </div>
      </section>

      <section className="story-section journey-section" aria-labelledby="journey-title">
        <div className="story-container journey-layout">
          <Reveal className="journey-panel glass-surface" direction="left">
            <div className="journey-panel-top">
              <span className="journey-avatar"><Salad size={18} /></span>
              <span><small>YOUR NUTRITION JOURNEY</small><strong>A little progress, each day</strong></span>
              <span className="journey-date"><CalendarDays size={14} /> This week</span>
            </div>
            <div className="journey-summary">
              <span><small>DAILY GOAL PREVIEW</small><strong>1,420 <i>/ 2,000 kcal</i></strong></span>
              <span className="journey-summary-badge"><Check size={13} /> Steady pace</span>
            </div>
            <div className="journey-goal-track"><i /></div>
            <div className="journey-chart-head"><span>Weekly rhythm</span><span>Sample progress</span></div>
            <div className="journey-chart" role="img" aria-label="Illustrative weekly goal progress for seven days">
              {week.map(({ day, amount }, index) => (
                <span className={`journey-bar${index === 5 ? ' journey-bar--highlight' : ''}`} key={`${day}-${index}`}>
                  <i style={{ '--bar-height': `${amount}%` }} />
                  <small>{day}</small>
                </span>
              ))}
            </div>
            <div className="journey-meals">
              <span className="journey-meals-heading"><span>Recent meal ideas</span><span>Example</span></span>
              <div><span className="meal-thumb"><Leaf size={14} /></span><span><strong>Fresh greens &amp; grains</strong><small>Lunch · an idea to explore</small></span><ArrowUpRight size={15} /></div>
              <div><span className="meal-thumb meal-thumb--soft"><Wheat size={14} /></span><span><strong>Colorful chickpea bowl</strong><small>Today · illustrative sample</small></span><ArrowUpRight size={15} /></div>
            </div>
            <p className="journey-disclaimer">Illustrative preview only — your actual tracker stays yours.</p>
          </Reveal>

          <Reveal className="story-copy journey-copy" direction="right" delay={0.08}>
            <span className="eyebrow"><span className="eyebrow-dot" /> Little steps add up</span>
            <h2 id="journey-title">Every meal<br /><span>moves you forward.</span></h2>
            <p>Keep your meals, daily goals, and progress together in one calm space that’s built around your own routine.</p>
            <div className="journey-points">
              <span><CheckCircle2 size={17} /> Follow your daily goals</span>
              <span><CheckCircle2 size={17} /> See meals you’ve logged</span>
              <span><CheckCircle2 size={17} /> Notice your week taking shape</span>
            </div>
            <button className="button button-primary" type="button" onClick={onNavigateToDaily}>Open your nutrition journey <ArrowRight size={16} /></button>
          </Reveal>
        </div>
      </section>

      <section className="closing-section" aria-labelledby="closing-title">
        <div className="story-container">
          <Reveal className="closing-card">
            <span className="closing-orb closing-orb--one" aria-hidden="true" />
            <span className="closing-orb closing-orb--two" aria-hidden="true" />
            <span className="closing-mark"><Salad size={22} /></span>
            <span className="eyebrow">A thoughtful next step starts here</span>
            <h2 id="closing-title">Your next meal,<br /><span>made smarter.</span></h2>
            <p>Start with what’s on your plate today. Your nutrition journey can begin with one simple photo.</p>
            <button className="button button-light" type="button" onClick={onNavigateToAnalyzer}>Try NutriAI <ArrowRight size={16} /></button>
            <span className="closing-footnote"><CheckCircle2 size={14} /> Your goals. Your pace. Your everyday.</span>
          </Reveal>
        </div>
      </section>
    </div>
  );
}
