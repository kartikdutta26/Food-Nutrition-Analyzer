import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import Navbar from './components/Navbar';
import AuthPage from './components/AuthPage';
import HeroLanding from './components/HeroLanding';
import FoodAnalyzer from './components/FoodAnalyzer';
import NutritionResults from './components/NutritionResults';
import DailyDashboard from './components/DailyDashboard';
import ProfileSettings from './components/ProfileSettings';
import OnboardingScreen from './components/OnboardingScreen';
import Footer from './components/Footer';
import { PRESET_MEALS, INITIAL_USER_PROFILE, INITIAL_TODAY_LOG } from './data/mockMeals';
import { authClient, authConfigured } from './auth/authClient';

function HomeBackground({ reducedMotion }) {
  const backgroundRef = useRef(null);

  useEffect(() => {
    const background = backgroundRef.current;
    if (!background || reducedMotion) return undefined;

    const getTargetOffset = () => {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const progress = maxScroll > 0 ? window.scrollY / maxScroll : 0;
      return Math.max(0, Math.min(progress, 1)) * 150;
    };

    let targetOffset = getTargetOffset();
    let displayedOffset = targetOffset;
    let animationFrame = 0;
    const render = () => {
      displayedOffset += (targetOffset - displayedOffset) * 0.12;
      background.style.transform = `translate3d(0, ${-displayedOffset}px, 0)`;

      if (Math.abs(targetOffset - displayedOffset) > 0.1) {
        animationFrame = window.requestAnimationFrame(render);
      } else {
        animationFrame = 0;
      }
    };
    const updateTarget = () => {
      targetOffset = getTargetOffset();
      if (!animationFrame) animationFrame = window.requestAnimationFrame(render);
    };

    background.style.transform = `translate3d(0, ${-displayedOffset}px, 0)`;
    window.addEventListener('scroll', updateTarget, { passive: true });
    window.addEventListener('resize', updateTarget);

    return () => {
      window.removeEventListener('scroll', updateTarget);
      window.removeEventListener('resize', updateTarget);
      if (animationFrame) window.cancelAnimationFrame(animationFrame);
    };
  }, [reducedMotion]);

  return <div ref={backgroundRef} className="home-background" aria-hidden="true" />;
}

function getPreferredTheme() {
  try {
    const savedTheme = window.localStorage.getItem('nutriai-theme');
    if (savedTheme === 'light' || savedTheme === 'dark') return savedTheme;
  } catch (error) {
    console.warn('Unable to read the saved theme preference:', error);
  }

  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  return 'light';
}

export default function App() {
  const [authSession, setAuthSession] = useState(null);
  const [demoMode, setDemoMode] = useState(false);
  const [authLoading, setAuthLoading] = useState(Boolean(authClient?.auth));
  const [pathname, setPathname] = useState(window.location.pathname);
  const [theme, setTheme] = useState(getPreferredTheme);
  const [profileState, setProfileState] = useState({ userId: null, loading: false, onboardingCompleted: true, foodPreferences: [] });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#080a0a' : '#ffffff');
  }, [theme]);

  const handleToggleTheme = () => {
    setTheme((currentTheme) => {
      const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
      try {
        window.localStorage.setItem('nutriai-theme', nextTheme);
      } catch (error) {
        console.warn('Unable to save the theme preference:', error);
      }
      return nextTheme;
    });
  };

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname);
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    const userId = authSession?.user?.id;
    if (!userId || !authClient) {
      setProfileState({ userId: null, loading: false, onboardingCompleted: true, foodPreferences: [] });
      return undefined;
    }

    let active = true;
    setProfileState({ userId, loading: true, onboardingCompleted: true, foodPreferences: [] });
    authClient.from('profiles')
      .select('food_preferences, onboarding_completed')
      .eq('id', userId)
      .maybeSingle()
      .then(({ data, error }) => {
        if (!active) return;
        if (error) {
          console.error('Unable to load food preferences:', error.message);
          setProfileState({ userId, loading: false, onboardingCompleted: true, foodPreferences: [] });
          return;
        }
        setProfileState({
          userId,
          loading: false,
          onboardingCompleted: data?.onboarding_completed !== false,
          foodPreferences: Array.isArray(data?.food_preferences) ? data.food_preferences : [],
        });
      })
      .catch((error) => {
        if (!active) return;
        console.error('Unable to load food preferences:', error);
        setProfileState({ userId, loading: false, onboardingCompleted: true, foodPreferences: [] });
      });

    return () => { active = false; };
  }, [authSession?.user?.id]);

  useEffect(() => {
    if (!authClient?.auth) {
      return undefined;
    }

    let active = true;
    const { data: { subscription } } = authClient.auth.onAuthStateChange((_event, session) => {
      if (active) setAuthSession(session);
    });

    authClient.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      if (error) {
        console.error('Unable to restore the authentication session:', error.message);
        setAuthSession(null);
      } else {
        setAuthSession(data.session);
      }
      setAuthLoading(false);
    }).catch((error) => {
      if (!active) return;
      console.error('Unable to restore the authentication session:', error);
      setAuthSession(null);
      setAuthLoading(false);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  const hasAppAccess = Boolean(authSession?.user) || (import.meta.env.DEV && demoMode);
  const profileReady = !authSession?.user || (profileState.userId === authSession.user.id && !profileState.loading);

  useEffect(() => {
    if (authLoading) return;
    const targetPath = hasAppAccess ? '/' : '/login';
    if (pathname !== targetPath) {
      window.history.replaceState({}, '', targetPath);
    }
  }, [authLoading, hasAppAccess, pathname]);

  // Navigation: 'home' | 'analyzer' | 'results' | 'daily' | 'profile'
  const [activeTab, setActiveTab] = useState('home');
  
  // App Global State
  const [activeMeal, setActiveMeal] = useState(PRESET_MEALS[0]); // Default: Paneer Rice Bowl
  const [userProfile, setUserProfile] = useState(INITIAL_USER_PROFILE);
  const [todayLog, setTodayLog] = useState(INITIAL_TODAY_LOG);
  const [toastMessage, setToastMessage] = useState(null);
  const reducedMotion = useReducedMotion();

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  // Scroll to top on tab change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [activeTab]);

  useEffect(() => {
    const main = document.querySelector('.app-main');
    if (reducedMotion || !main || !('IntersectionObserver' in window)) return undefined;

    const selector = '.bg-white.rounded-2xl, .bg-white.rounded-3xl, .bg-white.rounded-xl';
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -24px 0px' });

    const observeCards = (node) => {
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      const cards = [];
      if (node.matches(selector)) cards.push(node);
      cards.push(...node.querySelectorAll(selector));
      cards.forEach((card, index) => {
        if (card.classList.contains('card-reveal')) return;
        card.classList.add('card-reveal');
        card.style.setProperty('--reveal-delay', `${Math.min(index % 4, 3) * 65}ms`);
        revealObserver.observe(card);
      });
    };

    observeCards(main);
    const contentObserver = new MutationObserver((records) => {
      records.forEach((record) => record.addedNodes.forEach(observeCards));
    });
    contentObserver.observe(main, { childList: true, subtree: true });

    return () => {
      contentObserver.disconnect();
      revealObserver.disconnect();
    };
  }, [activeTab, reducedMotion]);

  // Flow: Analyzer -> Results
  const handleMealAnalyzed = (mealData) => {
    setActiveMeal(mealData);
    setActiveTab('results');
    showToast(`✨ Successfully analyzed ${mealData.name}!`);
  };

  // Flow: Results -> Log to Daily
  const handleLogMeal = (mealToLog) => {
    const updatedMeals = [
      ...todayLog.meals,
      {
        id: `meal-${Date.now()}`,
        slot: mealToLog.slot || 'Lunch',
        time: mealToLog.loggedAt || 'Just now',
        icon: '🥗',
        name: mealToLog.name,
        calories: mealToLog.calories,
        protein: mealToLog.protein,
        carbs: mealToLog.carbs,
        fats: mealToLog.fats,
        image: mealToLog.image
      }
    ];

    setTodayLog({
      ...todayLog,
      consumedCalories: todayLog.consumedCalories + mealToLog.calories,
      consumedProtein: todayLog.consumedProtein + mealToLog.protein,
      consumedCarbs: todayLog.consumedCarbs + mealToLog.carbs,
      consumedFats: todayLog.consumedFats + mealToLog.fats,
      meals: updatedMeals
    });

    showToast(`🎉 Logged ${mealToLog.name} (${mealToLog.calories} kcal) to today's dashboard!`);
  };

  // Remove meal from daily log
  const handleRemoveMeal = (mealId) => {
    const mealToRemove = todayLog.meals.find(m => m.id === mealId);
    if (!mealToRemove) return;

    setTodayLog({
      ...todayLog,
      consumedCalories: Math.max(0, todayLog.consumedCalories - (mealToRemove.calories || 0)),
      consumedProtein: Math.max(0, todayLog.consumedProtein - (mealToRemove.protein || 0)),
      consumedCarbs: Math.max(0, todayLog.consumedCarbs - (mealToRemove.carbs || 0)),
      consumedFats: Math.max(0, todayLog.consumedFats - (mealToRemove.fats || 0)),
      meals: todayLog.meals.filter(m => m.id !== mealId)
    });

    showToast(`Removed ${mealToRemove.name} from daily log.`);
  };

  // Quick manual add from daily dashboard
  const handleAddMealFromDaily = (newMeal) => {
    setTodayLog({
      ...todayLog,
      consumedCalories: todayLog.consumedCalories + newMeal.calories,
      consumedProtein: todayLog.consumedProtein + newMeal.protein,
      consumedCarbs: todayLog.consumedCarbs + newMeal.carbs,
      consumedFats: todayLog.consumedFats + newMeal.fats,
      meals: [...todayLog.meals, newMeal]
    });

    showToast(`Added ${newMeal.name} to ${newMeal.slot}!`);
  };

  // Profile update
  const handleUpdateProfile = (updatedData) => {
    setUserProfile(updatedData);
    showToast(`Profile updated! Goal set to ${updatedData.goal}.`);
  };

  const handleAuthenticate = async ({ mode, fullName, email, password }) => {
    if (!authClient?.auth) {
      return {
        type: 'error',
        message: 'Authentication is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to .env.local, then restart the dev server.',
      };
    }

    const result = mode === 'signup'
      ? await authClient.auth.signUp({ email, password, options: { data: { full_name: fullName } } })
      : await authClient.auth.signInWithPassword({ email, password });

    if (result.error) return { type: 'error', message: result.error.message };
    if (mode === 'signup' && !result.data.session) {
      return { type: 'success', message: 'Your account was created. Check your email to confirm it, then log in.' };
    }
    window.history.pushState({}, '', '/');
    setPathname('/');
    return {};
  };

  const handleCompleteOnboarding = async (preferences) => {
    const userId = authSession?.user?.id;
    if (!userId || !authClient) return { type: 'error', message: 'Sign in again to save your food preferences.' };

    const foodPreferences = [...new Set(preferences)];
    const { data, error } = await authClient.from('profiles')
      .update({ food_preferences: foodPreferences, onboarding_completed: true })
      .eq('id', userId)
      .select('id')
      .maybeSingle();

    if (error || !data) {
      return { type: 'error', message: error?.message || 'Your preferences could not be saved. Please try again.' };
    }

    setProfileState({ userId, loading: false, onboardingCompleted: true, foodPreferences });
    window.history.replaceState({}, '', '/');
    setPathname('/');
    return { type: 'success' };
  };

  const handlePasswordReset = async (email) => {
    if (!authClient?.auth) {
      return {
        type: 'error',
        message: 'Password reset is unavailable until an authentication provider is configured.',
      };
    }

    const { error } = await authClient.auth.resetPasswordForEmail(email);
    if (error) return { type: 'error', message: error.message };
    return { type: 'success', message: 'If an account exists for this address, a password reset email is on its way.' };
  };

  const handleSignOut = async () => {
    if (authClient?.auth) {
      const { error } = await authClient.auth.signOut();
      if (error) {
        showToast(`Could not sign out: ${error.message}`);
        return;
      }
    }
    setDemoMode(false);
    window.history.replaceState({}, '', '/login');
    setPathname('/login');
  };

  const handleExploreDemo = () => {
    window.history.pushState({}, '', '/');
    setPathname('/');
    setDemoMode(true);
  };

  if (authLoading || (authSession?.user && !profileReady)) {
    return (
      <main className="auth-loading" role="status">
        <span className="auth-spinner" aria-hidden="true" />
        {authLoading ? 'Restoring your secure session…' : 'Preparing your nutrition space…'}
      </main>
    );
  }

  if (!hasAppAccess) {
    return (
      <AuthPage
        onAuthenticate={handleAuthenticate}
        onResetPassword={handlePasswordReset}
        onExploreDemo={import.meta.env.DEV ? handleExploreDemo : undefined}
        authConfigured={authConfigured}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />
    );
  }

  if (authSession?.user && !profileState.onboardingCompleted) {
    return (
      <OnboardingScreen
        initialPreferences={profileState.foodPreferences}
        onComplete={handleCompleteOnboarding}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />
    );
  }

  return (
    <div className={`app-shell min-h-screen flex flex-col text-slate-800 font-sans selection:bg-teal-100 selection:text-teal-900${activeTab === 'home' ? ' app-shell--home' : ''}`}>
      {activeTab === 'home' && <HomeBackground reducedMotion={reducedMotion} />}
      <div className="app-content flex min-h-screen flex-col">
      
      {/* Toast Notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className="fixed top-24 right-4 z-50 px-4 py-3 rounded-2xl bg-teal-900 text-white shadow-2xl border border-teal-700/60 flex items-center gap-3 text-xs font-bold"
          >
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Navigation */}
      <Navbar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        onSignOut={handleSignOut}
        demoMode={demoMode}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />

      {/* Dynamic Content Views */}
      <main className="app-main flex-grow">
        <AnimatePresence mode="wait">
          
          {/* VIEW 1: 🏠 Home / Landing Page */}
          {activeTab === 'home' && (
            <motion.div
              key="home"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <HeroLanding 
                onNavigateToAnalyzer={() => setActiveTab('analyzer')} 
                onNavigateToDaily={() => setActiveTab('daily')}
                setActiveTab={setActiveTab}
              />
            </motion.div>
          )}

          {/* VIEW 2: 📸 Food Analyzer Page */}
          {activeTab === 'analyzer' && (
            <motion.div
              key="analyzer"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3 }}
            >
              <FoodAnalyzer 
                onAnalysisComplete={handleMealAnalyzed}
              />
            </motion.div>
          )}

          {/* VIEW 3: 📊 Nutrition Results Dashboard */}
          {activeTab === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3 }}
            >
              <NutritionResults 
                meal={activeMeal}
                onLogMeal={handleLogMeal}
                onScanAnother={() => setActiveTab('analyzer')}
                onNavigateToDashboard={() => setActiveTab('daily')}
              />
            </motion.div>
          )}

          {/* VIEW 4: 📅 Daily Nutrition / Dashboard */}
          {activeTab === 'daily' && (
            <motion.div
              key="daily"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3 }}
            >
              <DailyDashboard 
                todayLog={todayLog}
                userProfile={userProfile}
                onAddMealFromDaily={handleAddMealFromDaily}
                onNavigateToAnalyzer={() => setActiveTab('analyzer')}
                onRemoveMeal={handleRemoveMeal}
              />
            </motion.div>
          )}

          {/* VIEW 5: 👤 Profile / Preferences */}
          {activeTab === 'profile' && (
            <motion.div
              key="profile"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3 }}
            >
              <ProfileSettings 
                userProfile={userProfile}
                onUpdateProfile={handleUpdateProfile}
              />
            </motion.div>
          )}

        </AnimatePresence>
      </main>

      {/* Footer */}
      <Footer setActiveTab={setActiveTab} />

      </div>

    </div>
  );
}
