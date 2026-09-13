import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Navbar from './components/Navbar';
import HeroLanding from './components/HeroLanding';
import FoodAnalyzer from './components/FoodAnalyzer';
import NutritionResults from './components/NutritionResults';
import DailyDashboard from './components/DailyDashboard';
import ProfileSettings from './components/ProfileSettings';
import Footer from './components/Footer';
import { PRESET_MEALS, INITIAL_USER_PROFILE, INITIAL_TODAY_LOG } from './data/mockMeals';

export default function App() {
  // Navigation: 'home' | 'analyzer' | 'results' | 'daily' | 'profile'
  const [activeTab, setActiveTab] = useState('home');
  
  // App Global State
  const [activeMeal, setActiveMeal] = useState(PRESET_MEALS[0]); // Default: Paneer Rice Bowl
  const [userProfile, setUserProfile] = useState(INITIAL_USER_PROFILE);
  const [todayLog, setTodayLog] = useState(INITIAL_TODAY_LOG);
  const [toastMessage, setToastMessage] = useState(null);

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

  return (
    <div className="min-h-screen flex flex-col bg-[#fcfdfd] text-slate-800 font-sans selection:bg-teal-100 selection:text-teal-900">
      
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
      />

      {/* Dynamic Content Views */}
      <main className="flex-grow">
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
  );
}
