import { useMemo, useState } from 'react';
import { Check, ChevronRight, MoonStar, Salad, Sparkles, SunMedium } from 'lucide-react';

const categoryOptions = [
  {
    id: 'cereals',
    name: 'Cereals',
    blurb: 'Balanced grains and hearty staples',
    image: 'https://images.unsplash.com/photo-1517673400267-0251440c45dc?auto=format&fit=crop&w=900&q=80',
  },
  {
    id: 'fruits-vegetables',
    name: 'Fruits & Vegetables',
    blurb: 'Fresh produce and colorful nutrition',
    image: 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=80',
  },
  {
    id: 'simple-dishes',
    name: 'Simple Dishes',
    blurb: 'Easy everyday comfort meals',
    image: 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=900&q=80',
  },
  {
    id: 'seafood',
    name: 'Seafood',
    blurb: 'Light, protein-rich favorites',
    image: 'https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=900&q=80',
  },
  {
    id: 'herbal-tea',
    name: 'Herbal Tea',
    blurb: 'Calming drinks and wellness rituals',
    image: 'https://images.unsplash.com/photo-1515823064-d6e0c04616a7?auto=format&fit=crop&w=900&q=80',
  },
];

export default function OnboardingScreen({ initialPreferences = [], onComplete, theme, onToggleTheme }) {
  const [selected, setSelected] = useState(() => Array.isArray(initialPreferences) ? initialPreferences : []);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState('');
  const isDark = theme === 'dark';

  const preferenceSet = useMemo(() => new Set(selected), [selected]);

  const togglePreference = (id) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return [...next];
    });
    setFeedback('');
  };

  const handleComplete = async (skip = false) => {
    setIsSubmitting(true);
    setFeedback('');

    try {
      const result = await onComplete(skip ? [] : selected);
      if (result?.type === 'error') {
        setFeedback(result.message || 'Your preferences could not be saved. Please try again.');
        return;
      }
    } catch (error) {
      setFeedback(error.message || 'Your preferences could not be saved. Please try again.');
      return;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="onboarding-shell">
      <section className="onboarding-panel" aria-label="Food preference onboarding">
        <div className="onboarding-topbar">
          <div className="onboarding-brand" aria-label="NutriAI">
            <span className="onboarding-brand-mark"><Salad size={20} /></span>
            <span>Nutri<span style={{ color: 'var(--primary)' }}>AI</span></span>
          </div>

          <button
            type="button"
            className="theme-toggle"
            onClick={onToggleTheme}
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
          >
            {isDark ? <SunMedium size={15} /> : <MoonStar size={15} />}
            <span>{isDark ? 'Light' : 'Dark'}</span>
          </button>
        </div>

        <div>
          <p className="auth-eyebrow" style={{ marginBottom: '10px' }}>
            <Sparkles size={14} /> Personalized nutrition
          </p>
          <h1 className="onboarding-title">What do you enjoy <span>eating</span>?</h1>
          <p className="onboarding-copy">
            Pick the food categories you like most so NutriAI can tailor meal suggestions, smart analysis, and healthier routines to your taste.
          </p>
        </div>

        <div className="onboarding-scroller" role="list" aria-label="Food preference categories">
          {categoryOptions.map((category) => {
            const isSelected = preferenceSet.has(category.id);

            return (
              <button
                key={category.id}
                type="button"
                className={`onboarding-card${isSelected ? ' is-selected' : ''}`}
                onClick={() => togglePreference(category.id)}
                aria-pressed={isSelected}
                role="listitem"
              >
                <img className="onboarding-card-image" src={category.image} alt={category.name} />
                <div className="onboarding-card-body">
                  <div className="onboarding-card-copy">
                    <h3>{category.name}</h3>
                    <p>{category.blurb}</p>
                  </div>
                  <span className="onboarding-check" aria-hidden="true">
                    <Check size={16} />
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {feedback && <p className="onboarding-feedback" role="status">{feedback}</p>}

        <div className="onboarding-actions">
          <button type="button" className="onboarding-button onboarding-button--ghost" onClick={() => handleComplete(true)} disabled={isSubmitting}>
            Skip for now
          </button>
          <button type="button" className="onboarding-button onboarding-button--primary" onClick={() => handleComplete(false)} disabled={isSubmitting}>
            {isSubmitting ? 'Saving…' : 'Continue'}
            <ChevronRight size={16} />
          </button>
        </div>
      </section>
    </main>
  );
}
