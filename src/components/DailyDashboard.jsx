import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Flame, 
  Dumbbell, 
  Wheat, 
  Droplet, 
  Plus, 
  Trash2, 
  Calendar as CalendarIcon, 
  TrendingUp, 
  Camera, 
  CheckCircle2, 
  Sparkles 
} from 'lucide-react';
import { popButtonVariants } from '../animations/motionVariants';
import { getTargetProgress, hasNutritionTargets } from '../utils/nutritionTargets';

export default function DailyDashboard({ 
  todayLog, 
  dailyTotals,
  dailyDate,
  isLoading = false,
  loadError = '',
  actionError = '',
  isSavingMeal = false,
  pendingMealId = null,
  profileLoading = false,
  profileLoaded = false,
  profileError = '',
  onRetryProfile,
  onNavigateToProfile,
  onRetry,
  onAddMealFromDaily, 
  onNavigateToAnalyzer, 
  onRemoveMeal,
  userProfile 
}) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [quickMealName, setQuickMealName] = useState('');
  const [quickMealSlot, setQuickMealSlot] = useState('Dinner');
  const [quickMealNutrition, setQuickMealNutrition] = useState({
    calories: '',
    protein: '',
    carbs: '',
    fats: '',
  });
  const [formError, setFormError] = useState('');

  const targets = userProfile?.targets || null;

  const totalCalories = Number(dailyTotals?.calories || 0);
  const totalProtein = Number(dailyTotals?.protein || 0);
  const totalCarbs = Number(dailyTotals?.carbs || 0);
  const totalFats = Number(dailyTotals?.fats || 0);

  const progressFor = (key, total) => getTargetProgress(targets?.[key], total, profileLoaded);
  const calProgress = progressFor('calories', totalCalories);
  const proteinProgress = progressFor('protein', totalProtein);
  const carbsProgress = progressFor('carbs', totalCarbs);
  const fatsProgress = progressFor('fats', totalFats);
  const calPercent = calProgress.percent;
  const proteinPercent = proteinProgress.percent;
  const carbsPercent = carbsProgress.percent;
  const fatsPercent = fatsProgress.percent;
  const formatTarget = (key) => {
    const progress = getTargetProgress(targets?.[key], 0, profileLoaded);
    return progress.configured ? formatAmount(progress.target) : '—';
  };
  const progressLabel = (progress, total, target, unit) => progress.configured
    ? `${progress.percent}% (${formatAmount(total)} / ${formatTarget(target)} ${unit})`
    : `${progress.label} • ${formatAmount(total)} ${unit}`;
  const targetsConfigured = hasNutritionTargets(targets);

  const formatAmount = (value) => Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: 1,
  });

  const handleQuickAdd = async (e) => {
    e.preventDefault();
    const nutrition = Object.fromEntries(
      Object.entries(quickMealNutrition).map(([key, value]) => [key, Number(value)]),
    );

    if (!quickMealName.trim()) {
      setFormError('Enter a meal name.');
      return;
    }
    if (Object.entries(quickMealNutrition).some(([key, value]) => (
      value === '' || !Number.isFinite(nutrition[key]) || nutrition[key] < 0
    ))) {
      setFormError('Enter non-negative numbers for calories, protein, carbohydrates, and fats.');
      return;
    }

    setFormError('');
    const saved = await onAddMealFromDaily({
      name: quickMealName.trim(),
      meal_slot: quickMealSlot,
      nutrition,
    });

    if (saved) {
      setShowAddModal(false);
      setQuickMealName('');
      setQuickMealNutrition({ calories: '', protein: '', carbs: '', fats: '' });
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold uppercase tracking-wider mb-2">
            <CalendarIcon className="w-3.5 h-3.5 text-teal-600" />
            <span>Today's Nutrition • Saved meal log</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-black font-display text-slate-900 tracking-tight">
            Today's Nutrition
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Nutrition logs for {dailyDate} (UTC), loaded from your saved meals.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <motion.button
            variants={popButtonVariants}
            initial="initial"
            whileHover="hover"
            whileTap="tap"
            onClick={onNavigateToAnalyzer}
            className="btn-pop flex items-center gap-2 px-5 py-3 rounded-full bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs tracking-wide shadow-pop cursor-pointer"
          >
            <Camera className="w-4 h-4" />
            <span>Look up a food</span>
          </motion.button>
        </div>
      </div>

      {(isLoading || loadError || actionError || profileLoading || profileError) && (
        <div className="space-y-2 mb-6" aria-live="polite">
          {isLoading && (
            <p role="status" className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">
              Loading meals and daily nutrition…
            </p>
          )}
          {loadError && (
            <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              <span>{loadError}</span>
              <button type="button" onClick={onRetry} disabled={isLoading} className="font-bold underline disabled:opacity-50">
                Retry
              </button>
            </div>
          )}
          {actionError && (
            <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              {actionError}
            </p>
          )}
          {profileLoading && <p role="status" className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">Loading saved nutrition targets…</p>}
          {profileError && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>Saved targets could not be loaded: {profileError}</span><button type="button" onClick={onRetryProfile} disabled={profileLoading} className="font-bold underline disabled:opacity-50">Retry</button></div>}
        </div>
      )}

      {profileLoaded && !targetsConfigured && (
        <p role="status" className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 flex flex-wrap items-center justify-between gap-3">
          <span>Daily nutrition targets are not configured. Enter your targets in Profile to see progress.</span>
          <button type="button" onClick={onNavigateToProfile} className="font-bold underline">Configure targets</button>
        </p>
      )}

      {/* Grid: Overview & Progress Bars */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-10">
        
        {/* Left Card: Daily calories and target comparisons */}
        <div className="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft space-y-7">
          
          {/* Calorie Headline Callout */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-teal-50 via-emerald-50 to-teal-50 border border-teal-200/80">
            <div>
              <span className="text-xs font-extrabold uppercase tracking-wider text-teal-800">
                Caloric Intake Today
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-4xl font-black font-display text-slate-900">
                  {totalCalories.toLocaleString()}
                </span>
                <span className="text-lg font-bold text-slate-400">
                  / {formatTarget('calories')} kcal
                </span>
              </div>
            </div>

            <div className="text-right">
                <span className="text-xs font-bold text-slate-500 block">Remaining Target</span>
              <span className="text-2xl font-black text-teal-700">
                  {calProgress.configured ? formatAmount(Math.max(0, calProgress.target - totalCalories)) : '—'} <span className="text-xs font-normal">kcal</span>
              </span>
            </div>
          </div>

          {/* User Requested Progress Bars */}
          <div className="space-y-5">
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-500">
              Macronutrient Allocation Bars
            </h3>

            {/* Calories Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-800 flex items-center gap-1.5">
                  <Flame className="w-4 h-4 text-teal-600" />
                  Calories (Overall)
                </span>
                <span className="text-teal-700 font-extrabold">{progressLabel(calProgress, totalCalories, 'calories', 'kcal')}</span>
              </div>
              <div className="w-full h-3.5 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${calPercent ?? 0}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className="h-full bg-gradient-to-r from-teal-600 to-teal-400 rounded-full shadow-sm"
                />
              </div>
            </div>

            {/* Protein Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-800 flex items-center gap-1.5">
                  <Dumbbell className="w-4 h-4 text-emerald-600" />
                  Protein
                </span>
                <span className="text-emerald-700 font-extrabold">{progressLabel(proteinProgress, totalProtein, 'protein', 'g')}</span>
              </div>
              <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${proteinPercent ?? 0}%` }}
                  transition={{ duration: 1, delay: 0.1, ease: 'easeOut' }}
                  className="h-full bg-gradient-to-r from-emerald-600 to-teal-500 rounded-full"
                />
              </div>
            </div>

            {/* Carbs Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-800 flex items-center gap-1.5">
                  <Wheat className="w-4 h-4 text-amber-500" />
                  Carbohydrates
                </span>
                <span className="text-amber-700 font-extrabold">{progressLabel(carbsProgress, totalCarbs, 'carbs', 'g')}</span>
              </div>
              <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${carbsPercent ?? 0}%` }}
                  transition={{ duration: 1, delay: 0.2, ease: 'easeOut' }}
                  className="h-full bg-gradient-to-r from-amber-500 to-amber-300 rounded-full"
                />
              </div>
            </div>

            {/* Fats Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-slate-800 flex items-center gap-1.5">
                  <Droplet className="w-4 h-4 text-orange-500" />
                  Fats
                </span>
                <span className="text-orange-700 font-extrabold">{progressLabel(fatsProgress, totalFats, 'fats', 'g')}</span>
              </div>
              <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${fatsPercent ?? 0}%` }}
                  transition={{ duration: 1, delay: 0.3, ease: 'easeOut' }}
                  className="h-full bg-gradient-to-r from-orange-500 to-amber-400 rounded-full"
                />
              </div>
            </div>

          </div>

        </div>

        {/* Right Card: Nutrition Coach Advice & Hydration */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Nutrition summary card */}
          <div className="bg-white rounded-3xl p-6 border border-teal-100 shadow-card-soft">
            <div className="flex items-center gap-2 text-teal-800 text-xs font-bold uppercase tracking-wider mb-2">
              <Sparkles className="w-4 h-4 text-teal-600" />
              <span>Daily Nutrition Summary</span>
            </div>
            <h4 className="font-black text-slate-900 text-base mb-2">
              Logged intake so far
            </h4>
            <p className="text-slate-600 text-xs leading-relaxed">
              Saved meal records contain <span className="font-bold text-slate-800">{formatAmount(totalProtein)}g protein</span>.{' '}
              {calProgress.configured
                ? <><span className="font-bold text-teal-700">{formatAmount(Math.max(0, calProgress.target - totalCalories))} kcal</span> remain against your saved calorie target.</>
                : profileLoaded ? 'Configure your targets in Profile to compare intake.' : 'Saved targets are not loaded yet.'} The backend does not generate meal recommendations.
            </p>
          </div>

          {/* Water Tracker */}
          <div className="bg-white rounded-3xl p-6 border border-teal-100 shadow-card-soft flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-cyan-50 text-cyan-600 flex items-center justify-center font-bold">
                💧
              </div>
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Hydration Tracking</span>
                <p className="text-xl font-black text-slate-900">
                  Not available
                </p>
                <p className="text-[11px] text-teal-700 font-semibold">Water intake is not stored by the backend.</p>
              </div>
            </div>
            <div className="px-3 py-1 rounded-full bg-cyan-100 text-cyan-800 text-xs font-bold">
              Not tracked
            </div>
          </div>

        </div>

      </div>

      {/* TODAY'S MEALS TIMELINE (User Requested Format) */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-xl font-black font-display text-slate-900">Today's Meals</h3>
            <p className="text-xs text-slate-500">Your saved breakfasts, lunches, snacks, and dinners for {dailyDate} UTC.</p>
          </div>

          <motion.button
            variants={popButtonVariants}
            initial="initial"
            whileHover="hover"
            whileTap="tap"
            onClick={() => { setFormError(''); setShowAddModal(true); }}
            disabled={isSavingMeal || isLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-50 hover:bg-teal-100 text-teal-800 font-bold text-xs border border-teal-200 cursor-pointer"
          >
            <Plus className="w-4 h-4 text-teal-600" />
            <span>Log Meal Manually</span>
          </motion.button>
        </div>

        {/* Meal List */}
        <div className="space-y-3">
          {isLoading ? (
            <p role="status" className="rounded-2xl border border-teal-100 bg-teal-50/30 p-5 text-center text-sm text-slate-500">
              Retrieving saved meals…
            </p>
          ) : loadError ? (
            <p className="rounded-2xl border border-rose-100 bg-rose-50/50 p-5 text-center text-sm text-rose-700">
              Meal history is unavailable until the backend request succeeds.
            </p>
          ) : todayLog.meals.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-teal-200 bg-teal-50/20 p-5 text-center text-sm text-slate-500">
              No meals are logged for this UTC day yet. Add a meal using nutrition values from a trusted source.
            </p>
          ) : todayLog.meals.map((meal) => (
            <motion.div
              key={meal.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-2xl border border-teal-50 bg-teal-50/20 hover:bg-teal-50/50 transition-colors flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-4">
                <span className="text-2xl">{meal.icon || '🍽️'}</span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-teal-800 uppercase tracking-wide">
                      {meal.slot}
                    </span>
                    <span className="text-[11px] text-slate-400">• {meal.time || 'Logged'}{meal.time ? ' UTC' : ''}</span>
                  </div>
                  <h4 className="font-bold text-slate-900 text-sm sm:text-base">
                    {meal.name}
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {formatAmount(meal.protein)}g Protein • {formatAmount(meal.carbs)}g Carbs • {formatAmount(meal.fats)}g Fats
                  </p>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    {meal.dataSource === 'sample_preset'
                      ? 'Sample preset nutrition'
                      : meal.dataSource === 'usda_food_data_central'
                        ? `USDA FoodData Central${meal.serving?.description ? ` • ${meal.serving.description}` : ''}`
                        : 'User-provided nutrition'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right">
                  <span className="text-base font-black text-slate-900">{formatAmount(meal.calories)}</span>
                  <span className="text-xs text-slate-500 font-medium ml-1">kcal</span>
                </div>

                <button
                  onClick={() => onRemoveMeal(meal.id)}
                  disabled={pendingMealId === meal.id}
                  className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                  title={pendingMealId === meal.id ? 'Removing entry' : 'Remove entry'}
                  aria-label={`Remove ${meal.name}`}
                >
                  {pendingMealId === meal.id ? '…' : <Trash2 className="w-4 h-4" />}
                </button>
              </div>
            </motion.div>
          ))}

          {/* Dinner Placeholder / Add Meal button if dinner not logged */}
          {!isLoading && !loadError && !todayLog.meals.some(m => m.slot === 'Dinner') && (
            <div className="p-4 rounded-2xl border-2 border-dashed border-teal-200 bg-teal-50/20 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🌙</span>
                <div>
                  <span className="text-xs font-black text-teal-800 uppercase tracking-wide">
                    Dinner
                  </span>
                  <h4 className="font-bold text-slate-700 text-sm">Not logged yet</h4>
                </div>
              </div>

              <motion.button
                variants={popButtonVariants}
                initial="initial"
                whileHover="hover"
                whileTap="tap"
                onClick={() => { setFormError(''); setShowAddModal(true); }}
                className="px-4 py-2 rounded-xl bg-teal-600 text-white text-xs font-bold shadow-sm"
              >
                + Add Dinner
              </motion.button>
            </div>
          )}
        </div>
      </div>

      {/* Inline Quick Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white rounded-3xl p-6 sm:p-8 max-h-[90vh] max-w-md w-full overflow-y-auto shadow-2xl border border-teal-100"
          >
            <h3 className="text-xl font-black text-slate-900 mb-4">Log Meal Entry</h3>
            
            <form onSubmit={handleQuickAdd} className="space-y-4">
              <p className="text-xs leading-relaxed text-slate-500">
                Enter nutrition values from a trusted source. NutriAI does not estimate these values in this form.
              </p>
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Meal Name</label>
                <input
                  type="text"
                  required
                  value={quickMealName}
                  onChange={(e) => setQuickMealName(e.target.value)}
                  maxLength={120}
                  placeholder="e.g. Mixed Dal with 2 Rotis"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Meal Slot</label>
                  <select
                    value={quickMealSlot}
                    onChange={(e) => setQuickMealSlot(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                  >
                    <option value="Breakfast">Breakfast 🌅</option>
                    <option value="Lunch">Lunch ☀️</option>
                    <option value="Dinner">Dinner 🌙</option>
                    <option value="Snack">Snack 🍎</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Calories (kcal) *</label>
                  <input
                    type="number"
                    required
                    min="0"
                    max="100000"
                    step="any"
                    value={quickMealNutrition.calories}
                    onChange={(e) => setQuickMealNutrition({ ...quickMealNutrition, calories: e.target.value })}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {[
                  { key: 'protein', label: 'Protein (g)', max: '10000' },
                  { key: 'carbs', label: 'Carbohydrates (g)', max: '10000' },
                  { key: 'fats', label: 'Fats (g)', max: '10000' },
                ].map(({ key, label, max }) => (
                  <div key={key}>
                    <label className="block text-xs font-bold text-slate-600 uppercase mb-1">{label} *</label>
                    <input
                      type="number"
                      required
                      min="0"
                      max={max}
                      step="any"
                      value={quickMealNutrition[key]}
                      onChange={(e) => setQuickMealNutrition({ ...quickMealNutrition, [key]: e.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                    />
                  </div>
                ))}
              </div>

              {formError && <p role="alert" className="text-xs text-rose-700">{formError}</p>}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="w-1/2 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingMeal}
                  className="w-1/2 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs shadow-sm disabled:cursor-wait disabled:opacity-60"
                >
                  {isSavingMeal ? 'Saving…' : 'Save Entry'}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

    </div>
  );
}
