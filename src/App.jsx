import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import Navbar from './components/Navbar';
import AuthPage from './components/AuthPage';
import HeroLanding from './components/HeroLanding';
import FoodAnalyzer from './components/FoodAnalyzer';
import NutritionResults from './components/NutritionResults';
import DailyDashboard from './components/DailyDashboard';
import ProfileSettings from './components/ProfileSettings';
import Footer from './components/Footer';
import { PRESET_MEALS, INITIAL_USER_PROFILE, INITIAL_TODAY_LOG } from './data/mockMeals';
import { authClient, authConfigured } from './auth/authClient';

function AmbientBackground({ activeTab }) {
  return (
    <div className={`ambient-backdrop${activeTab === 'home' ? ' ambient-backdrop--food' : ''}`} aria-hidden="true">
      <div className="ambient-orb ambient-orb--aqua" />
      <div className="ambient-orb ambient-orb--peach" />
      <div className="ambient-wave ambient-wave--one" />
      <div className="ambient-wave ambient-wave--two" />
      <div className="ambient-specks" />
    </div>
  );
}

export default function App() {
  const [authSession, setAuthSession] = useState(null);
  const [demoMode, setDemoMode] = useState(false);
  const [authLoading, setAuthLoading] = useState(Boolean(authClient?.auth));
  const [pathname, setPathname] = useState(window.location.pathname);

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname);
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

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
    return {};
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
    setDemoMode(false);
    if (!authClient?.auth) return;
    const { error } = await authClient.auth.signOut();
    if (error) showToast(`Could not sign out: ${error.message}`);
  };

  const handleExploreDemo = () => {
    window.history.replaceState({}, '', '/');
    setPathname('/');
    setDemoMode(true);
  };

  if (authLoading) {
    return (
      <main className="auth-loading" role="status">
        <span className="auth-spinner" aria-hidden="true" />
        Restoring your secure session…
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
      />
    );
  }

  return (
    <div className={`app-shell min-h-screen flex flex-col text-slate-800 font-sans selection:bg-teal-100 selection:text-teal-900${activeTab === 'home' ? ' app-shell--home' : ''}`}>
      <AmbientBackground activeTab={activeTab} />
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
