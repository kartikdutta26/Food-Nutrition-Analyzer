import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useMotionValue, useReducedMotion, useScroll, useSpring, useTransform } from 'framer-motion';
import Navbar from './components/Navbar';
import HeroLanding from './components/HeroLanding';
import FoodAnalyzer from './components/FoodAnalyzer';
import NutritionResults from './components/NutritionResults';
import DailyDashboard from './components/DailyDashboard';
import ProfileSettings from './components/ProfileSettings';
import Footer from './components/Footer';
import { PRESET_MEALS, INITIAL_USER_PROFILE, INITIAL_TODAY_LOG } from './data/mockMeals';

function AmbientBackground() {
  const reducedMotion = useReducedMotion();
  const { scrollY } = useScroll();
  const aquaY = useTransform(scrollY, [0, 1600], [0, 150]);
  const peachY = useTransform(scrollY, [0, 1600], [0, -120]);
  const pointerX = useMotionValue(-500);
  const pointerY = useMotionValue(-500);
  const glowX = useSpring(pointerX, { stiffness: 28, damping: 22, mass: 0.8 });
  const glowY = useSpring(pointerY, { stiffness: 28, damping: 22, mass: 0.8 });

  useEffect(() => {
    if (reducedMotion || !window.matchMedia('(pointer: fine)').matches) return undefined;
    const moveGlow = (event) => {
      pointerX.set(event.clientX);
      pointerY.set(event.clientY);
    };
    window.addEventListener('pointermove', moveGlow, { passive: true });
    return () => window.removeEventListener('pointermove', moveGlow);
  }, [pointerX, pointerY, reducedMotion]);

  return (
    <div className="ambient-backdrop" aria-hidden="true">
      <motion.div className="ambient-orb ambient-orb--aqua" style={reducedMotion ? undefined : { y: aquaY }} />
      <motion.div className="ambient-orb ambient-orb--peach" style={reducedMotion ? undefined : { y: peachY }} />
      <div className="flow-art-layer flow-art-layer--one">
      <motion.svg className="flow-art flow-art--aqua" viewBox="0 0 1600 1050" preserveAspectRatio="none" style={reducedMotion ? undefined : { y: aquaY }}>
        <defs>
          <linearGradient id="aqua-ribbon" x1="0" x2="1" y1="0" y2="1"><stop stopColor="#9eddd2" stopOpacity=".1" /><stop offset=".55" stopColor="#78cdbd" stopOpacity=".29" /><stop offset="1" stopColor="#ddf7f3" stopOpacity=".12" /></linearGradient>
          <linearGradient id="peach-ribbon" x1="0" x2="1" y1="1" y2="0"><stop stopColor="#ffb59c" stopOpacity=".04" /><stop offset=".5" stopColor="#ffb59c" stopOpacity=".3" /><stop offset="1" stopColor="#ffe2d4" stopOpacity=".1" /></linearGradient>
        </defs>
        <path d="M-100 695 C68 585 185 605 340 726 C492 846 613 963 819 918 C1033 871 1161 689 1388 711 C1493 722 1571 778 1700 825 L1700 1100 L-100 1100Z" fill="url(#aqua-ribbon)" />
        <path d="M540 1100 C674 1002 759 919 960 910 C1194 898 1367 771 1537 766 C1597 764 1647 785 1700 816 L1700 1100Z" fill="url(#peach-ribbon)" />
        <path d="M-100 119 C22 167 46 235 40 318 C34 381 71 430 122 479 C13 482 -60 430 -100 375Z" fill="url(#aqua-ribbon)" opacity=".47" />
        <path d="M1175 -10 C1281 35 1372 101 1487 103 C1570 105 1632 75 1700 27 L1700 263 C1608 306 1520 299 1440 260 C1340 211 1251 204 1175 171 C1125 148 1126 46 1175 -10Z" fill="url(#peach-ribbon)" />
        <path d="M-95 669 C86 566 193 599 348 720 C507 844 623 928 822 884 C1031 838 1163 657 1394 682 C1504 694 1583 747 1700 790" fill="none" stroke="rgba(255,255,255,.63)" strokeWidth="2" />
        <path d="M-80 727 C87 624 193 655 347 775 C506 899 627 982 834 938 C1045 894 1178 713 1404 739 C1512 751 1594 800 1700 846" fill="none" stroke="rgba(91,177,160,.21)" strokeWidth="1.5" />
        <path d="M519 1046 C681 946 780 871 963 866 C1197 860 1360 735 1538 729 C1601 728 1650 749 1700 777" fill="none" stroke="rgba(255,255,255,.62)" strokeWidth="2" />
        <path d="M1151 22 C1242 58 1358 128 1479 128 C1565 128 1634 97 1697 55" fill="none" stroke="rgba(255,255,255,.58)" strokeWidth="2" />
        <path d="M1131 68 C1229 106 1353 171 1473 171 C1557 171 1630 140 1697 101" fill="none" stroke="rgba(89,180,164,.22)" strokeWidth="1.5" />
      </motion.svg>
      </div>
      <div className="flow-art-layer flow-art-layer--two">
      <motion.svg className="flow-art flow-art--detail" viewBox="0 0 1600 1050" preserveAspectRatio="none" style={reducedMotion ? undefined : { y: peachY }}>
        <path d="M-115 188 C55 121 162 145 265 226 C365 305 472 331 611 283 C731 242 839 132 968 123 C1076 115 1165 167 1253 221" fill="none" stroke="rgba(90,190,174,.24)" strokeWidth="1.7" />
        <path d="M1084 182 C1159 214 1218 246 1297 268 C1410 299 1546 287 1727 238" fill="none" stroke="rgba(255,181,156,.32)" strokeWidth="1.8" />
        <path d="M-150 791 C88 624 234 647 421 790 C594 923 713 1001 905 963 C1110 922 1229 756 1443 762 C1547 764 1636 806 1740 866" fill="none" stroke="rgba(255,255,255,.58)" strokeWidth="2" />
        <path d="M-120 852 C102 687 247 711 430 850 C603 982 727 1054 922 1017 C1129 979 1248 814 1456 821 C1561 823 1642 860 1737 919" fill="none" stroke="rgba(202,141,115,.16)" strokeWidth="1.5" />
      </motion.svg>
      </div>
      <svg className="botanical-art" viewBox="0 0 1600 1050" preserveAspectRatio="none">
        <defs>
          <linearGradient id="leaf-green" x1="0" x2="1" y1="0" y2="1"><stop stopColor="#99bd8e" /><stop offset="1" stopColor="#42794d" /></linearGradient>
          <linearGradient id="leaf-light" x1="0" x2="1" y1="0" y2="1"><stop stopColor="#d1e4c8" /><stop offset="1" stopColor="#75a977" /></linearGradient>
          <filter id="leaf-soft"><feGaussianBlur stdDeviation="5" /></filter>
        </defs>
        <g fill="url(#leaf-light)" opacity=".42" filter="url(#leaf-soft)">
          <path d="M-34 45 C47 13 111 35 139 100 C83 116 21 98 -34 45Z" />
          <path d="M-26 93 C48 69 103 89 125 151 C71 166 18 146 -26 93Z" />
          <path d="M1544 36 C1486 51 1456 91 1461 146 C1514 145 1551 107 1544 36Z" />
          <path d="M1593 79 C1527 89 1494 129 1500 187 C1552 187 1591 150 1593 79Z" />
          <path d="M-25 903 C63 860 132 876 169 936 C104 968 33 955 -25 903Z" />
          <path d="M1536 913 C1471 883 1417 897 1389 951 C1443 979 1501 964 1536 913Z" />
        </g>
        <g fill="url(#leaf-green)" opacity=".24">
          <path d="M-12 17 C53 22 95 61 101 121 C55 113 19 78 -12 17Z" />
          <path d="M-9 72 C52 79 87 117 86 174 C43 164 11 127 -9 72Z" />
          <path d="M1510 -20 C1472 38 1478 91 1524 127 C1550 84 1545 28 1510 -20Z" />
          <path d="M1571 20 C1526 68 1520 119 1555 165 C1589 127 1595 73 1571 20Z" />
          <path d="M-20 962 C45 920 99 928 132 977 C82 1012 26 1007 -20 962Z" />
          <path d="M1587 969 C1528 930 1478 939 1448 985 C1495 1019 1547 1013 1587 969Z" />
        </g>
      </svg>
      <div className="ambient-grain" />
      {!reducedMotion && <motion.div className="cursor-glow" style={{ x: glowX, y: glowY }} />}
    </div>
  );
}

export default function App() {
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

  return (
    <div className="app-shell min-h-screen flex flex-col text-slate-800 font-sans selection:bg-teal-100 selection:text-teal-900">
      <AmbientBackground />
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
