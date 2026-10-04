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

export default function DailyDashboard({ 
  todayLog, 
  onAddMealFromDaily, 
  onNavigateToAnalyzer, 
  onRemoveMeal,
  userProfile 
}) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [quickMealName, setQuickMealName] = useState('');
  const [quickMealSlot, setQuickMealSlot] = useState('Dinner');
  const [quickMealCals, setQuickMealCals] = useState('450');
  const [quickMealProtein, setQuickMealProtein] = useState('22');

  const targets = userProfile?.targets || {
    calories: 2000,
    protein: 100,
    carbs: 220,
    fats: 65,
    water: 2.5
  };

  // Calculate totals from meals
  const totalCalories = todayLog.meals.reduce((acc, m) => acc + (m.calories || 0), 0);
  const totalProtein = todayLog.meals.reduce((acc, m) => acc + (m.protein || 0), 0);
  const totalCarbs = todayLog.meals.reduce((acc, m) => acc + (m.carbs || 0), 0);
  const totalFats = todayLog.meals.reduce((acc, m) => acc + (m.fats || 0), 0);

  const calPercent = Math.min(Math.round((totalCalories / targets.calories) * 100), 100);
  const proteinPercent = Math.min(Math.round((totalProtein / targets.protein) * 100), 100);
  const carbsPercent = Math.min(Math.round((totalCarbs / targets.carbs) * 100), 100);
  const fatsPercent = Math.min(Math.round((totalFats / targets.fats) * 100), 100);

  const handleQuickAdd = (e) => {
    e.preventDefault();
    if (!quickMealName) return;

    const newMeal = {
      id: `manual-${Date.now()}`,
      name: quickMealName,
      slot: quickMealSlot,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      icon: quickMealSlot === 'Breakfast' ? '🌅' : quickMealSlot === 'Lunch' ? '☀️' : '🌙',
      calories: parseInt(quickMealCals, 10) || 400,
      protein: parseInt(quickMealProtein, 10) || 15,
      carbs: 45,
      fats: 12,
      image: 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=300&q=80'
    };

    onAddMealFromDaily(newMeal);
    setShowAddModal(false);
    setQuickMealName('');
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold uppercase tracking-wider mb-2">
            <CalendarIcon className="w-3.5 h-3.5 text-teal-600" />
            <span>Today's Nutrition • Complete Daily Log</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-black font-display text-slate-900 tracking-tight">
            Today's Nutrition
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Track daily calorie budget and macronutrient distribution in real-time.
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
            <span>Scan with AI Camera</span>
          </motion.button>
        </div>
      </div>

      {/* Grid: Overview & Progress Bars */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-10">
        
        {/* Left Card: 1,420 / 2,000 kcal & Macro Progress Bars */}
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
                  / {targets.calories.toLocaleString()} kcal
                </span>
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs font-bold text-slate-500 block">Remaining Budget</span>
              <span className="text-2xl font-black text-teal-700">
                {Math.max(0, targets.calories - totalCalories)} <span className="text-xs font-normal">kcal</span>
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
                <span className="text-teal-700 font-extrabold">{calPercent}% ({totalCalories} / {targets.calories} kcal)</span>
              </div>
              <div className="w-full h-3.5 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${calPercent}%` }}
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
                <span className="text-emerald-700 font-extrabold">{proteinPercent}% ({totalProtein} / {targets.protein} g)</span>
              </div>
              <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${proteinPercent}%` }}
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
                <span className="text-amber-700 font-extrabold">{carbsPercent}% ({totalCarbs} / {targets.carbs} g)</span>
              </div>
              <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${carbsPercent}%` }}
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
                <span className="text-orange-700 font-extrabold">{fatsPercent}% ({totalFats} / {targets.fats} g)</span>
              </div>
              <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${fatsPercent}%` }}
                  transition={{ duration: 1, delay: 0.3, ease: 'easeOut' }}
                  className="h-full bg-gradient-to-r from-orange-500 to-amber-400 rounded-full"
                />
              </div>
            </div>

          </div>

        </div>

        {/* Right Card: Nutrition Coach Advice & Hydration */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* AI Coach Suggestion Card */}
          <div className="bg-white rounded-3xl p-6 border border-teal-100 shadow-card-soft">
            <div className="flex items-center gap-2 text-teal-800 text-xs font-bold uppercase tracking-wider mb-2">
              <Sparkles className="w-4 h-4 text-teal-600" />
              <span>AI Meal Recommendation</span>
            </div>
            <h4 className="font-black text-slate-900 text-base mb-2">
              Optimal Dinner Strategy 🌙
            </h4>
            <p className="text-slate-600 text-xs leading-relaxed">
              You've consumed <span className="font-bold text-slate-800">{totalProtein}g protein</span> and have{' '}
              <span className="font-bold text-teal-700">{Math.max(0, targets.calories - totalCalories)} kcal</span> remaining. 
              Aim for a low-carb, vegetable-rich dinner like <strong className="text-slate-900">Palak Paneer with a single Multigrain Roti</strong> or grilled fish.
            </p>
          </div>

          {/* Water Tracker */}
          <div className="bg-white rounded-3xl p-6 border border-teal-100 shadow-card-soft flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-cyan-50 text-cyan-600 flex items-center justify-center font-bold">
                💧
              </div>
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Hydration Target</span>
                <p className="text-xl font-black text-slate-900">
                  {todayLog.consumedWater} / {targets.water} L
                </p>
                <p className="text-[11px] text-teal-700 font-semibold">72% of daily target reached</p>
              </div>
            </div>
            <div className="px-3 py-1 rounded-full bg-cyan-100 text-cyan-800 text-xs font-bold">
              Optimal
            </div>
          </div>

        </div>

      </div>

      {/* TODAY'S MEALS TIMELINE (User Requested Format) */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-xl font-black font-display text-slate-900">Today's Meals</h3>
            <p className="text-xs text-slate-500">Your logged breakfasts, lunches, snacks, and dinners.</p>
          </div>

          <motion.button
            variants={popButtonVariants}
            initial="initial"
            whileHover="hover"
            whileTap="tap"
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-50 hover:bg-teal-100 text-teal-800 font-bold text-xs border border-teal-200 cursor-pointer"
          >
            <Plus className="w-4 h-4 text-teal-600" />
            <span>Log Meal Manually</span>
          </motion.button>
        </div>

        {/* Meal List */}
        <div className="space-y-3">
          {todayLog.meals.map((meal) => (
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
                    <span className="text-[11px] text-slate-400">• {meal.time || 'Logged'}</span>
                  </div>
                  <h4 className="font-bold text-slate-900 text-sm sm:text-base">
                    {meal.name}
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {meal.protein}g Protein • {meal.carbs}g Carbs • {meal.fats}g Fats
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right">
                  <span className="text-base font-black text-slate-900">{meal.calories}</span>
                  <span className="text-xs text-slate-500 font-medium ml-1">kcal</span>
                </div>

                <button
                  onClick={() => onRemoveMeal(meal.id)}
                  className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                  title="Remove entry"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          ))}

          {/* Dinner Placeholder / Add Meal button if dinner not logged */}
          {!todayLog.meals.some(m => m.slot === 'Dinner') && (
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
                onClick={() => setShowAddModal(true)}
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
            className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-teal-100"
          >
            <h3 className="text-xl font-black text-slate-900 mb-4">Log Meal Entry</h3>
            
            <form onSubmit={handleQuickAdd} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Meal Name</label>
                <input
                  type="text"
                  required
                  value={quickMealName}
                  onChange={(e) => setQuickMealName(e.target.value)}
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
                  <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Calories (kcal)</label>
                  <input
                    type="number"
                    value={quickMealCals}
                    onChange={(e) => setQuickMealCals(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Protein (g)</label>
                <input
                  type="number"
                  value={quickMealProtein}
                  onChange={(e) => setQuickMealProtein(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                />
              </div>

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
                  className="w-1/2 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs shadow-sm"
                >
                  Save Entry
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

    </div>
  );
}
