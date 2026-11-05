import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence, useMotionValue, useReducedMotion, useScroll, useSpring, useTransform } from 'framer-motion';
import { ShieldCheck } from 'lucide-react';
import Navbar from './components/Navbar';
import AuthPage from './components/AuthPage';
import HeroLanding from './components/HeroLanding';
import FoodAnalyzer from './components/FoodAnalyzer';
import NutritionResults from './components/NutritionResults';
import DailyDashboard from './components/DailyDashboard';
import ProfileSettings from './components/ProfileSettings';
import AuthScreen from './components/AuthScreen';
import Footer from './components/Footer';
import { EMPTY_USER_PROFILE, profileFromApi, profileUpdateToApi } from './utils/profile';
import { createRequestSequence } from './utils/requestSequence';
import { createPersonalDataScope, resetPersonalDataState } from './utils/personalDataScope';
import {
  cleanAuthRedirectUrl,
  cleanEmailConfirmationTokenFromUrl,
  createIdempotentCallbackProcessor,
  friendlyAuthError,
  getEmailConfirmationCallback,
  getAuthRedirectInfo,
  getRegistrationSuccessMessage,
  hasSupabaseAuthCallbackPayload,
  loginWithEmail,
  registerWithEmail,
  resendSignupVerification,
  sendPasswordReset,
  signOutLocally,
  subscribeToVerifiedAuthState,
  updatePassword,
  verifyEmailWithTokenHash,
} from './lib/authFlows';
import {
  analyzeFood,
  createMeal,
  deleteMeal,
  fetchDailyNutrition,
  fetchMealsForDate,
  fetchProfile,
  updateProfile,
} from './api/client';

const EMPTY_NUTRITION_TOTALS = {
  calories: 0,
  protein: 0,
  carbs: 0,
  fats: 0,
  fiber: 0,
};

const AUTH_REQUIRED_TABS = new Set(['daily', 'profile']);
const PERSONAL_DATA_API_ENABLED = true;

function toDashboardMeal(meal) {
  const consumedAt = new Date(meal.consumed_at);

  return {
    id: meal.id,
    name: meal.name,
    slot: meal.meal_slot,
    time: Number.isNaN(consumedAt.getTime())
      ? 'Logged'
      : consumedAt.toLocaleTimeString([], { timeZone: 'UTC', hour: '2-digit', minute: '2-digit' }),
    calories: meal.nutrition.calories,
    protein: meal.nutrition.protein,
    carbs: meal.nutrition.carbs,
    fats: meal.nutrition.fats,
    fiber: meal.nutrition.fiber,
    dataSource: meal.data_source,
    fdcId: meal.fdc_id,
    serving: meal.serving,
  };
}

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

function PersonalDataPending({ section, onExploreFood }) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <section aria-labelledby="personal-data-pending-title" className="rounded-3xl border border-white/80 bg-white/80 p-7 text-center shadow-card-soft backdrop-blur-xl sm:p-10">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-white bg-teal-50 text-teal-800 shadow-sm">
          <ShieldCheck className="h-6 w-6" aria-hidden="true" />
        </div>
        <span className="inline-flex rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-[10px] font-extrabold uppercase tracking-[.15em] text-teal-800">Account connected</span>
        <h1 id="personal-data-pending-title" className="mt-4 text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">Your {section} is waiting for secure sync</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-slate-600">
          NutriAI is finishing account-specific access for saved profiles and meal history. Your personal nutrition data stays hidden until that connection is ready.
        </p>
        <button type="button" onClick={onExploreFood} className="mt-6 inline-flex items-center justify-center rounded-full border border-white/80 bg-gradient-to-r from-orange-200 to-teal-200 px-5 py-3 text-sm font-extrabold text-teal-950 shadow-sm">
          Explore food analysis
        </button>
      </section>
    </div>
  );
}

export default function App() {
  const [initialAuthRedirectInfo] = useState(() => getAuthRedirectInfo(
    globalThis.window?.location?.href || '',
  ));
  const [initialEmailConfirmationCallback] = useState(() => getEmailConfirmationCallback(
    globalThis.window?.location?.href || '',
  ));
  const [initialHasAuthCallbackPayload] = useState(() => hasSupabaseAuthCallbackPayload(
    globalThis.window?.location?.href || '',
  ));
  const [activeTab, setActiveTab] = useState(() => (
    initialAuthRedirectInfo.flow || initialAuthRedirectInfo.error ? 'auth' : 'home'
  ));
  const [authUser, setAuthUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authConfigured, setAuthConfigured] = useState(false);
  const [authMode, setAuthMode] = useState(() => (
    initialAuthRedirectInfo.flow === 'recovery'
      ? 'reset'
      : initialEmailConfirmationCallback
        ? 'verify'
        : 'login'
  ));
  const [authReturnTab, setAuthReturnTab] = useState('home');
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [recoveryReady, setRecoveryReady] = useState(false);
  const [authRedirectFlow, setAuthRedirectFlow] = useState(() => (
    initialAuthRedirectInfo.error ? null : initialAuthRedirectInfo.flow
  ));
  const [authRedirectNotice, setAuthRedirectNotice] = useState('');
  const [authRedirectError, setAuthRedirectError] = useState(initialAuthRedirectInfo.error || '');
  const pendingProtectedTab = useRef(null);
  const supabaseClientRef = useRef(null);
  const initialAuthSessionHandled = useRef(false);
  const passwordRecoveryHandled = useRef(false);
  const emailConfirmationToken = useRef(initialEmailConfirmationCallback);
  const emailConfirmationProcessor = useRef(null);
  if (!emailConfirmationProcessor.current) {
    emailConfirmationProcessor.current = createIdempotentCallbackProcessor();
  }

  const [demoMode, setDemoMode] = useState(false);
  
  // App Global State
  const [activeMeal, setActiveMeal] = useState(null);
  const [userProfile, setUserProfile] = useState({ ...EMPTY_USER_PROFILE });
  const [todayLog, setTodayLog] = useState({ meals: [] });
  const [dailyTotals, setDailyTotals] = useState(EMPTY_NUTRITION_TOTALS);
  const [dailyLoading, setDailyLoading] = useState(false);
  const [dailyError, setDailyError] = useState('');
  const [mealActionError, setMealActionError] = useState('');
  const [isSavingMeal, setIsSavingMeal] = useState(false);
  const [pendingMealId, setPendingMealId] = useState(null);
  const [isLoggingAnalysisMeal, setIsLoggingAnalysisMeal] = useState(false);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [profileActionError, setProfileActionError] = useState('');
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [dailyRequestSequence] = useState(createRequestSequence);
  const [profileRequestSequence] = useState(createRequestSequence);
  const personalDataScopeRef = useRef(null);
  if (!personalDataScopeRef.current) personalDataScopeRef.current = createPersonalDataScope();
  const expiredAuthUserId = useRef(null);
  const reducedMotion = useReducedMotion();
  const dailyDate = new Date().toISOString().slice(0, 10);
  const hasAppAccess = Boolean(authUser) || (import.meta.env.DEV && demoMode);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  const clearPersonalState = useCallback(() => {
    dailyRequestSequence.next();
    profileRequestSequence.next();
    resetPersonalDataState({
      setTodayLog,
      setDailyTotals,
      setDailyLoading,
      setDailyError,
      setMealActionError,
      setIsSavingMeal,
      setPendingMealId,
      setIsLoggingAnalysisMeal,
      setActiveMeal,
      setUserProfile,
      setProfileLoading,
      setProfileLoaded,
      setProfileError,
      setProfileActionError,
      setIsSavingProfile,
    }, {
      initialProfile: EMPTY_USER_PROFILE,
      emptyTotals: EMPTY_NUTRITION_TOTALS,
    });
    setToastMessage(null);
  }, [dailyRequestSequence, profileRequestSequence]);

  const openAuth = (mode = 'login', returnTab = 'home') => {
    setAuthReturnTab(returnTab);
    setAuthMode(mode);
    setAuthRedirectNotice('');
    setAuthRedirectError('');
    setActiveTab('auth');
  };

  const navigateToTab = (tab) => {
    if (AUTH_REQUIRED_TABS.has(tab) && authLoading) {
      pendingProtectedTab.current = tab;
      setAuthReturnTab(tab);
      setAuthMode('login');
      setActiveTab('auth');
      return;
    }
    if (AUTH_REQUIRED_TABS.has(tab) && !authUser) {
      openAuth('login', tab);
      return;
    }
    setActiveTab(tab);
  };

  const completeAuthentication = (successMessage = 'You are signed in to NutriAI.') => {
    const nextTab = AUTH_REQUIRED_TABS.has(authReturnTab) || authReturnTab === 'results'
      ? authReturnTab
      : 'home';
    setAuthRedirectNotice('');
    setAuthRedirectError('');
    setActiveTab(nextTab);
    showToast(successMessage);
  };

  const clearRedirectFromAddressBar = () => {
    const cleanUrl = cleanAuthRedirectUrl(window.location.href);
    window.history.replaceState({}, document.title, cleanUrl);
  };

  const clearEmailConfirmationTokenFromAddressBar = () => {
    const cleanUrl = cleanEmailConfirmationTokenFromUrl(window.location.href);
    window.history.replaceState({}, document.title, cleanUrl);
  };

  const getAuthRedirectOptions = () => ({
    publicAppUrl: import.meta.env.VITE_APP_PUBLIC_URL,
    isDevelopment: Boolean(import.meta.env.DEV),
  });

  const getSupabaseClient = () => {
    if (!supabaseClientRef.current) {
      throw new Error('Authentication is still starting. Wait a moment and try again.');
    }
    return supabaseClientRef.current;
  };

  const handleProtectedAuthFailure = useCallback((error, snapshot) => {
    if (![401, 403].includes(error?.status) || !personalDataScopeRef.current.isCurrent(snapshot)) return;
    if (expiredAuthUserId.current === snapshot.userId) return;

    expiredAuthUserId.current = snapshot.userId;
    if (error?.code === 'SESSION_USER_CHANGED') {
      personalDataScopeRef.current.invalidate();
      clearPersonalState();
      setAuthUser(null);
      if (activeTab === 'results') {
        setMealActionError('Your signed-in account changed. Try logging this food again.');
      }
      return;
    }

    const returnTab = AUTH_REQUIRED_TABS.has(activeTab) ? activeTab : null;
    personalDataScopeRef.current.invalidate();
    clearPersonalState();
    setAuthUser(null);

    if (returnTab) {
      setAuthReturnTab(returnTab);
      setAuthMode('login');
      setAuthRedirectNotice('');
      setAuthRedirectError('Your session expired. Sign in again to access your personal nutrition data.');
      setActiveTab('auth');
    } else if (activeTab === 'results') {
      setMealActionError('Your session expired. Sign in again to add this food to your meal history.');
    }

    const client = supabaseClientRef.current;
    if (client) void signOutLocally(client).catch(() => {});
  }, [activeTab, clearPersonalState]);

  useEffect(() => {
    const redirectInfo = initialAuthRedirectInfo;

    let active = true;
    let unsubscribe = () => {};

    if (emailConfirmationToken.current) clearEmailConfirmationTokenFromAddressBar();

    import('./lib/supabase.js').then(({ supabase }) => {
      if (!active) return;
      supabaseClientRef.current = supabase;
      setAuthConfigured(true);
      unsubscribe = subscribeToVerifiedAuthState(supabase, {
        onUser: (user) => {
          const nextUserId = user?.id ?? null;
          if (personalDataScopeRef.current.setUserId(nextUserId)) {
            expiredAuthUserId.current = null;
            clearPersonalState();
            setProfileLoading(Boolean(user));
          }
          setAuthUser(user);
        },
        onPasswordRecovery: (user) => {
          if (passwordRecoveryHandled.current) return;
          passwordRecoveryHandled.current = true;
          if (user) {
            setRecoveryReady(true);
            setAuthRedirectFlow(null);
            setAuthRedirectError('');
            setAuthRedirectNotice('');
            setAuthMode('reset');
            setActiveTab('auth');
            clearRedirectFromAddressBar();
          } else {
            setRecoveryReady(false);
            setAuthRedirectFlow(null);
            setAuthMode('forgot');
            setAuthRedirectError('This password reset link is not valid for a verified account. Request a new reset email.');
            setActiveTab('auth');
            clearRedirectFromAddressBar();
          }
        },
        onInitialSession: (user) => {
          if (initialAuthSessionHandled.current) return;
          initialAuthSessionHandled.current = true;
          setAuthLoading(false);

          if (redirectInfo.error) {
            setAuthRedirectFlow(null);
            setAuthMode(redirectInfo.flow === 'recovery' ? 'forgot' : 'login');
            setAuthRedirectError(redirectInfo.error);
            setAuthRedirectNotice('');
            setActiveTab('auth');
            clearRedirectFromAddressBar();
            return;
          }

          if (redirectInfo.flow === 'verify') {
            setAuthRedirectFlow(null);
            if (emailConfirmationToken.current) {
              setAuthMode('verify');
              setActiveTab('auth');
              clearRedirectFromAddressBar();
              return;
            }

            const sdkConsumedCallback = initialHasAuthCallbackPayload
              && !hasSupabaseAuthCallbackPayload(window.location.href);
            if (user && sdkConsumedCallback) {
              setAuthRedirectNotice('');
              setActiveTab('home');
              showToast('Your email was confirmed successfully. Welcome to NutriAI.');
            } else {
              setAuthMode('login');
              setAuthRedirectNotice(user
                ? 'This link did not return a confirmation response. Your current session is still checked separately; sign in or request a fresh confirmation email.'
                : 'No verified confirmation response was received. Sign in if you have already confirmed your email, or request a fresh confirmation email.');
              setActiveTab('auth');
            }
            clearRedirectFromAddressBar();
          } else if (redirectInfo.flow === 'recovery') {
            setAuthMode('reset');
            setActiveTab('auth');
          }

          const requestedTab = pendingProtectedTab.current;
          if (requestedTab) {
            pendingProtectedTab.current = null;
            if (user) {
              setActiveTab(requestedTab);
            } else {
              setAuthReturnTab(requestedTab);
              setAuthMode('login');
              setActiveTab('auth');
            }
          }
        },
      });
    }).catch(() => {
      if (!active) return;
      setAuthConfigured(false);
      setAuthLoading(false);
      setAuthRedirectFlow(null);
      setAuthMode(redirectInfo.flow === 'recovery' ? 'forgot' : 'login');
      setAuthRedirectError('Authentication could not start. Check the local Supabase configuration and reload.');
      setActiveTab('auth');
      clearRedirectFromAddressBar();
    });

    return () => {
      active = false;
      unsubscribe();
      supabaseClientRef.current = null;
    };
  }, [clearPersonalState, initialAuthRedirectInfo, initialHasAuthCallbackPayload]);

  useEffect(() => {
    if (authRedirectFlow !== 'recovery' || authLoading || recoveryReady) return undefined;
    const timer = window.setTimeout(() => {
      setAuthRedirectFlow(null);
      setAuthMode('forgot');
      setAuthRedirectError('The reset link could not be verified. Request a fresh password reset email and open its latest link.');
      clearRedirectFromAddressBar();
    }, 8000);
    return () => window.clearTimeout(timer);
  }, [authRedirectFlow, authLoading, recoveryReady]);

  useEffect(() => {
    if (authUser) return;
    if (AUTH_REQUIRED_TABS.has(activeTab)) setActiveTab('home');
  }, [authUser, activeTab]);

  useEffect(() => {
    if (
      !authLoading
      && authUser
      && activeTab === 'auth'
      && authMode !== 'reset'
      && authMode !== 'verify'
      && !authRedirectError
      && !authRedirectNotice
    ) {
      setActiveTab('home');
    }
  }, [authLoading, authUser, activeTab, authMode, authRedirectError, authRedirectNotice]);

  const loadDaily = useCallback(async (requestedScope) => {
    const snapshot = requestedScope || personalDataScopeRef.current.capture();
    if (
      !authUser
      || authUser.id !== snapshot.userId
      || !personalDataScopeRef.current.isCurrent(snapshot)
      || !PERSONAL_DATA_API_ENABLED
    ) return;
    const requestId = dailyRequestSequence.next();
    const isCurrentRequest = () => (
      dailyRequestSequence.isCurrent(requestId)
      && personalDataScopeRef.current.isCurrent(snapshot)
    );
    setDailyLoading(true);
    setDailyError('');

    try {
      const [mealResponse, nutritionResponse] = await Promise.all([
        fetchMealsForDate(dailyDate, { expectedUserId: snapshot.userId }),
        fetchDailyNutrition(dailyDate, { expectedUserId: snapshot.userId }),
      ]);

      if (!Array.isArray(mealResponse.items) || !nutritionResponse.totals) {
        throw new Error('The backend returned an unexpected daily nutrition response.');
      }

      if (!isCurrentRequest()) return;
      setTodayLog({ meals: mealResponse.items.map(toDashboardMeal) });
      setDailyTotals(nutritionResponse.totals);
    } catch (error) {
      handleProtectedAuthFailure(error, snapshot);
      if (isCurrentRequest()) {
        setDailyError(error instanceof Error ? error.message : 'Unable to load daily nutrition.');
      }
    } finally {
      if (isCurrentRequest()) setDailyLoading(false);
    }
  }, [authUser, dailyDate, dailyRequestSequence, handleProtectedAuthFailure]);

  const loadProfile = useCallback(async (requestedScope) => {
    const snapshot = requestedScope || personalDataScopeRef.current.capture();
    if (
      !authUser
      || authUser.id !== snapshot.userId
      || !personalDataScopeRef.current.isCurrent(snapshot)
      || !PERSONAL_DATA_API_ENABLED
    ) return;
    const requestId = profileRequestSequence.next();
    const isCurrentRequest = () => (
      profileRequestSequence.isCurrent(requestId)
      && personalDataScopeRef.current.isCurrent(snapshot)
    );
    setProfileLoading(true);
    setProfileError('');
    try {
      const profile = await fetchProfile({ expectedUserId: snapshot.userId });
      if (
        !profile
        || !Object.prototype.hasOwnProperty.call(profile, 'targets')
        || (profile.targets !== null && (typeof profile.targets !== 'object' || Array.isArray(profile.targets)))
        || !Array.isArray(profile.dietary_preferences)
      ) {
        throw new Error('The backend returned an unexpected profile response.');
      }
      if (!isCurrentRequest()) return;
      setUserProfile(profileFromApi(profile));
      setProfileLoaded(true);
    } catch (error) {
      handleProtectedAuthFailure(error, snapshot);
      if (isCurrentRequest()) {
        setProfileError(error instanceof Error ? error.message : 'Unable to load your profile.');
      }
    } finally {
      if (isCurrentRequest()) setProfileLoading(false);
    }
  }, [authUser, profileRequestSequence, handleProtectedAuthFailure]);

  useEffect(() => {
    if (activeTab === 'daily' && authUser && PERSONAL_DATA_API_ENABLED) void loadDaily();
  }, [activeTab, authUser, loadDaily]);

  useEffect(() => {
    if (PERSONAL_DATA_API_ENABLED && authUser) void loadProfile();
  }, [authUser, loadProfile]);

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
    const source = mealData.data_source === 'usda_food_data_central'
      ? 'USDA FoodData Central'
      : 'sample preset';
    showToast(`Loaded ${source} nutrition for ${mealData.name}.`);
  };

  const handleLogMeal = async (mealRequest) => {
    if (!authUser) {
      openAuth('login', 'results');
      return false;
    }
    const snapshot = personalDataScopeRef.current.capture();
    if (authUser.id !== snapshot.userId || !personalDataScopeRef.current.isCurrent(snapshot)) return false;
    if (!PERSONAL_DATA_API_ENABLED) {
      setMealActionError('Personal meal logging is paused until account-specific API access is enabled.');
      return false;
    }
    if (!mealRequest || (!mealRequest.preset_id && !mealRequest.name)) {
      setMealActionError('This food lookup is missing the meal information needed to log it.');
      return false;
    }
    setMealActionError('');
    setIsLoggingAnalysisMeal(true);
    try {
      const savedMeal = await createMeal(mealRequest, { expectedUserId: snapshot.userId });
      if (!personalDataScopeRef.current.isCurrent(snapshot)) return false;
      await loadDaily(snapshot);
      if (!personalDataScopeRef.current.isCurrent(snapshot)) return false;
      showToast(`Logged ${savedMeal.name} to today's nutrition.`);
      return true;
    } catch (error) {
      handleProtectedAuthFailure(error, snapshot);
      if (personalDataScopeRef.current.isCurrent(snapshot)) {
        setMealActionError(error instanceof Error ? error.message : 'Unable to log this preset meal.');
      }
      return false;
    } finally {
      if (personalDataScopeRef.current.isCurrent(snapshot)) setIsLoggingAnalysisMeal(false);
    }
  };

  const handleRemoveMeal = async (mealId) => {
    if (!authUser || !PERSONAL_DATA_API_ENABLED) return;
    const snapshot = personalDataScopeRef.current.capture();
    if (authUser.id !== snapshot.userId || !personalDataScopeRef.current.isCurrent(snapshot)) return;
    const mealToRemove = todayLog.meals.find((meal) => meal.id === mealId);
    setMealActionError('');
    setPendingMealId(mealId);

    try {
      await deleteMeal(mealId, { expectedUserId: snapshot.userId });
      if (!personalDataScopeRef.current.isCurrent(snapshot)) return;
      await loadDaily(snapshot);
      if (!personalDataScopeRef.current.isCurrent(snapshot)) return;
      showToast(`Removed ${mealToRemove?.name || 'meal'} from daily log.`);
    } catch (error) {
      handleProtectedAuthFailure(error, snapshot);
      if (personalDataScopeRef.current.isCurrent(snapshot)) {
        setMealActionError(error instanceof Error ? error.message : 'Unable to delete this meal.');
      }
    } finally {
      if (personalDataScopeRef.current.isCurrent(snapshot)) setPendingMealId(null);
    }
  };

  const handleAddMealFromDaily = async (mealRequest) => {
    if (!authUser || !PERSONAL_DATA_API_ENABLED) return false;
    const snapshot = personalDataScopeRef.current.capture();
    if (authUser.id !== snapshot.userId || !personalDataScopeRef.current.isCurrent(snapshot)) return false;
    setMealActionError('');
    setIsSavingMeal(true);

    try {
      const savedMeal = await createMeal(mealRequest, { expectedUserId: snapshot.userId });
      if (!personalDataScopeRef.current.isCurrent(snapshot)) return false;
      await loadDaily(snapshot);
      if (!personalDataScopeRef.current.isCurrent(snapshot)) return false;
      showToast(`Logged ${savedMeal.name} to today's nutrition.`);
      return true;
    } catch (error) {
      handleProtectedAuthFailure(error, snapshot);
      if (personalDataScopeRef.current.isCurrent(snapshot)) {
        setMealActionError(error instanceof Error ? error.message : 'Unable to save this meal.');
      }
      return false;
    } finally {
      if (personalDataScopeRef.current.isCurrent(snapshot)) setIsSavingMeal(false);
    }
  };

  const handleUpdateProfile = async (updatedData) => {
    if (!authUser || !PERSONAL_DATA_API_ENABLED) return false;
    const snapshot = personalDataScopeRef.current.capture();
    if (authUser.id !== snapshot.userId || !personalDataScopeRef.current.isCurrent(snapshot)) return false;
    setProfileActionError('');
    setIsSavingProfile(true);
    try {
      const savedProfile = await updateProfile(profileUpdateToApi(updatedData), {
        expectedUserId: snapshot.userId,
      });
      if (!personalDataScopeRef.current.isCurrent(snapshot)) return false;
      setUserProfile(profileFromApi(savedProfile));
      setProfileLoaded(true);
      showToast('Your profile and nutrition preferences have been saved.');
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to save your profile.';
      handleProtectedAuthFailure(error, snapshot);
      if (personalDataScopeRef.current.isCurrent(snapshot)) setProfileActionError(message);
      return false;
    } finally {
      if (personalDataScopeRef.current.isCurrent(snapshot)) setIsSavingProfile(false);
    }
  };

  const handleLogout = async () => {
    setIsSigningOut(true);
    personalDataScopeRef.current.invalidate();
    clearPersonalState();
    setAuthUser(null);
    setActiveTab('home');
    try {
      await signOutLocally(getSupabaseClient());
      showToast('You have been signed out.');
    } catch (error) {
      showToast(friendlyAuthError(error, 'logout'));
    } finally {
      setIsSigningOut(false);
    }
  };

  const handleEmailConfirmation = () => {
    const callback = emailConfirmationToken.current;
    if (!callback) {
      throw new Error('This confirmation link is no longer available. Open the latest email link or sign in if already confirmed.');
    }

    return emailConfirmationProcessor.current(async () => {
      try {
        const result = await verifyEmailWithTokenHash(getSupabaseClient(), callback);
        emailConfirmationToken.current = null;
        setAuthRedirectFlow(null);
        setAuthRedirectError('');
        clearRedirectFromAddressBar();
        if (result.authenticated) {
          setAuthMode('login');
          setActiveTab('home');
        } else {
          setAuthMode('login');
          setAuthRedirectNotice('Email confirmed successfully. Sign in to continue.');
          setActiveTab('auth');
        }
        return result;
      } catch (error) {
        emailConfirmationToken.current = null;
        setAuthRedirectFlow(null);
        setAuthMode('login');
        setAuthRedirectError(friendlyAuthError(error, 'verify'));
        setActiveTab('auth');
        clearRedirectFromAddressBar();
        throw error;
      }
    });
  };

  const handleResendVerification = (email) => resendSignupVerification(
    getSupabaseClient(),
    email,
    getAuthRedirectOptions(),
  ).then((result) => {
    setAuthRedirectError('');
    setAuthRedirectNotice('');
    return result;
  });

  const handlePasswordResetComplete = () => {
    setRecoveryReady(false);
    setAuthRedirectFlow(null);
    setAuthRedirectError('');
    setAuthRedirectNotice('');
    setActiveTab('home');
    showToast('Your password has been updated.');
  };

  const handleAuthPageAuthenticate = async ({ mode, fullName, email, password }) => {
    try {
      const client = getSupabaseClient();
      if (mode === 'signup') {
        const result = await registerWithEmail(
          client,
          { name: fullName, email, password },
          getAuthRedirectOptions(),
        );
        if (result.authenticated) completeAuthentication();
        return {
          type: 'success',
          message: getRegistrationSuccessMessage(email, result),
        };
      }

      await loginWithEmail(client, { email, password });
      completeAuthentication();
      return {};
    } catch (error) {
      return {
        type: 'error',
        message: friendlyAuthError(error, mode === 'signup' ? 'signup' : 'login'),
      };
    }
  };

  const handleAuthPagePasswordReset = async (email) => {
    try {
      await sendPasswordReset(getSupabaseClient(), email, getAuthRedirectOptions());
      return {
        type: 'success',
        message: 'If an account exists for this address, a password reset email is on its way.',
      };
    } catch (error) {
      return { type: 'error', message: friendlyAuthError(error, 'forgot') };
    }
  };

  const handleSignOut = async () => {
    if (demoMode) {
      setDemoMode(false);
      setActiveTab('home');
      return;
    }
    await handleLogout();
  };

  const handleExploreDemo = () => {
    setDemoMode(true);
    setActiveTab('home');
  };

  if (authLoading) {
    return (
      <main className="auth-loading" role="status">
        <span className="auth-spinner" aria-hidden="true" />
        Restoring your secure session…
      </main>
    );
  }

  if (!hasAppAccess && activeTab !== 'auth') {
    return (
      <AuthPage
        onAuthenticate={handleAuthPageAuthenticate}
        onResetPassword={handleAuthPagePasswordReset}
        onExploreDemo={import.meta.env.DEV ? handleExploreDemo : undefined}
        authConfigured={authConfigured}
        onOpenAdvancedAuth={() => {
          setAuthMode('login');
          setActiveTab('auth');
        }}
      />
    );
  }

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
        setActiveTab={navigateToTab}
        onSignOut={handleSignOut}
        demoMode={demoMode}
        isSigningOut={isSigningOut}
        authUser={authUser}
        profileName={profileLoaded ? userProfile.name : ''}
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
                onNavigateToAnalyzer={() => navigateToTab('analyzer')}
                onNavigateToDaily={() => navigateToTab('daily')}
                setActiveTab={navigateToTab}
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
                onAnalyzeFood={analyzeFood}
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
                key={`results-${authUser?.id || 'signed-out'}`}
                meal={activeMeal}
                onLogMeal={handleLogMeal}
                userTargets={PERSONAL_DATA_API_ENABLED && authUser ? userProfile.targets : null}
                profileLoading={PERSONAL_DATA_API_ENABLED && authUser ? profileLoading : false}
                profileLoaded={PERSONAL_DATA_API_ENABLED && authUser ? profileLoaded : false}
                profileError={PERSONAL_DATA_API_ENABLED && authUser ? profileError : ''}
                onRetryProfile={PERSONAL_DATA_API_ENABLED && authUser ? loadProfile : undefined}
                onNavigateToProfile={() => navigateToTab('profile')}
                logError={mealActionError}
                isLoggingMeal={isLoggingAnalysisMeal}
                canLogMeal={PERSONAL_DATA_API_ENABLED && Boolean(authUser)}
                isAuthenticated={Boolean(authUser)}
                onRequireAuth={() => openAuth('login', 'results')}
                onScanAnother={() => navigateToTab('analyzer')}
                onNavigateToDashboard={() => navigateToTab('daily')}
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
              {PERSONAL_DATA_API_ENABLED ? (
                <DailyDashboard
                  key={`daily-${authUser?.id || 'signed-out'}`}
                  todayLog={todayLog}
                  dailyTotals={dailyTotals}
                  dailyDate={dailyDate}
                  isLoading={dailyLoading}
                  loadError={dailyError}
                  actionError={mealActionError}
                  isSavingMeal={isSavingMeal}
                  pendingMealId={pendingMealId}
                  profileLoading={profileLoading}
                  profileLoaded={profileLoaded}
                  profileError={profileError}
                  onRetryProfile={loadProfile}
                  onNavigateToProfile={() => navigateToTab('profile')}
                  onRetry={loadDaily}
                  userProfile={userProfile}
                  onAddMealFromDaily={handleAddMealFromDaily}
                  onNavigateToAnalyzer={() => navigateToTab('analyzer')}
                  onRemoveMeal={handleRemoveMeal}
                />
              ) : (
                <PersonalDataPending section="nutrition journey" onExploreFood={() => navigateToTab('analyzer')} />
              )}
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
              {PERSONAL_DATA_API_ENABLED ? (
                <ProfileSettings
                  key={`profile-${authUser?.id || 'signed-out'}`}
                  userProfile={userProfile}
                  onUpdateProfile={handleUpdateProfile}
                  isLoading={profileLoading}
                  isLoaded={profileLoaded}
                  loadError={profileError}
                  actionError={profileActionError}
                  isSaving={isSavingProfile}
                  onRetry={loadProfile}
                />
              ) : (
                <PersonalDataPending section="profile" onExploreFood={() => navigateToTab('analyzer')} />
              )}
            </motion.div>
          )}

          {activeTab === 'auth' && (
            <motion.div
              key="auth"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3 }}
            >
              <AuthScreen
                mode={authMode}
                onModeChange={(mode) => {
                  setAuthMode(mode);
                  setAuthRedirectError('');
                  setAuthRedirectNotice('');
                }}
                onRegister={(values) => registerWithEmail(getSupabaseClient(), values, getAuthRedirectOptions())}
                onLogin={(values) => loginWithEmail(getSupabaseClient(), values)}
                onForgotPassword={(email) => sendPasswordReset(getSupabaseClient(), email, getAuthRedirectOptions())}
                onResendVerification={handleResendVerification}
                onConfirmEmail={handleEmailConfirmation}
                onResetPassword={(password) => updatePassword(getSupabaseClient(), password)}
                onAuthenticated={completeAuthentication}
                onPasswordResetComplete={handlePasswordResetComplete}
                authLoading={authLoading}
                recoveryReady={recoveryReady}
                redirectNotice={authRedirectNotice}
                redirectError={authRedirectError}
                onExploreFood={() => navigateToTab('analyzer')}
              />
            </motion.div>
          )}

        </AnimatePresence>
      </main>

      {/* Footer */}
      <Footer setActiveTab={navigateToTab} />

      </div>

      </div>
  );
}
