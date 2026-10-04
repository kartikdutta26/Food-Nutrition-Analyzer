import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Sparkles, 
  Flame, 
  Dumbbell, 
  Wheat, 
  Droplet, 
  Leaf, 
  CheckCircle, 
  PlusCircle, 
  ArrowLeft, 
  Share2, 
  Layers, 
  HeartHandshake,
  AlertCircle
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { popButtonVariants } from '../animations/motionVariants';

// Circular Gauge Component (Agent 1: Animation Part)
function CircularProgress({ value, max, label, unit, color, icon: Icon }) {
  const percentage = Math.min(Math.round((value / max) * 100), 100);
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-4 rounded-2xl bg-white border border-teal-100 shadow-card-soft">
      <div className="relative w-24 h-24 flex items-center justify-center">
        <svg className="w-full h-full -rotate-90">
          <circle
            cx="48"
            cy="48"
            r={radius}
            stroke="#f0fdfa"
            strokeWidth="8"
            fill="transparent"
          />
          <motion.circle
            cx="48"
            cy="48"
            r={radius}
            stroke={color}
            strokeWidth="8"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: strokeDashoffset }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
            strokeLinecap="round"
            fill="transparent"
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <Icon className="w-4 h-4 mb-0.5 text-slate-400" />
          <span className="text-base font-black text-slate-900 leading-none">{value}</span>
          <span className="text-[10px] text-slate-400 font-semibold">{unit}</span>
        </div>
      </div>

      <div className="mt-2 text-center">
        <span className="text-xs font-bold text-slate-700">{label}</span>
        <div className="text-[10px] text-slate-400 font-medium mt-0.5">
          {percentage}% daily
        </div>
      </div>
    </div>
  );
}

export default function NutritionResults({ 
  meal, 
  onLogMeal, 
  onScanAnother, 
  onNavigateToDashboard 
}) {
  const [portionMultiplier, setPortionMultiplier] = useState(1);
  const [hasLogged, setHasLogged] = useState(false);

  // Fallback defaults if meal is null
  const currentMeal = meal || {
    name: 'Paneer Rice',
    image: 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80',
    calories: 620,
    protein: 28,
    carbs: 72,
    fats: 22,
    fiber: 6,
    score: 8.2,
    insight: 'High in protein but slightly high in carbohydrates.',
    ingredients: ['Cottage Cheese (Paneer) - 120g', 'Basmati Steamed Rice - 180g', 'Aromatic Indian Spices', 'Olive & Ghee Glaze - 10ml'],
    micros: {
      calcium: '380 mg (38% DV)',
      iron: '3.6 mg (20% DV)',
      potassium: '460 mg (13% DV)',
      sodium: '490 mg',
    }
  };

  // Scaled macros
  const calories = Math.round(currentMeal.calories * portionMultiplier);
  const protein = Math.round(currentMeal.protein * portionMultiplier);
  const carbs = Math.round(currentMeal.carbs * portionMultiplier);
  const fats = Math.round(currentMeal.fats * portionMultiplier);
  const fiber = Math.round(currentMeal.fiber * portionMultiplier);

  const handleLogToDaily = () => {
    // Fire festive confetti animation
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.7 },
      colors: ['#0d9488', '#14b8a6', '#5eead4', '#10b981', '#f59e0b']
    });

    setHasLogged(true);

    const loggedItem = {
      ...currentMeal,
      calories,
      protein,
      carbs,
      fats,
      fiber,
      loggedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      slot: 'Lunch'
    };

    onLogMeal(loggedItem);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      
      {/* Top Breadcrumb & Action */}
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={onScanAnother}
          className="flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-teal-700 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Analyze Another Meal</span>
        </button>

        <div className="flex items-center gap-2 text-xs font-semibold text-teal-800 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-200">
          <Sparkles className="w-3.5 h-3.5 text-teal-600" />
          <span>Analysis Complete • Verified by NutriAI Model</span>
        </div>
      </div>

      {/* Main Meal Header Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft mb-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
          
          <div className="md:col-span-4 relative rounded-2xl overflow-hidden aspect-square border border-teal-200 shadow-md">
            <img
              src={currentMeal.image}
              alt={currentMeal.name}
              className="w-full h-full object-cover"
            />
            <div className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-slate-900/80 backdrop-blur-md text-white text-[11px] font-bold">
              AI Vision Matched
            </div>
          </div>

          <div className="md:col-span-8 space-y-4">
            <div>
              <span className="text-xs font-extrabold uppercase tracking-wider text-teal-700">
                Verified Dish Analysis
              </span>
              <h1 className="text-3xl sm:text-4xl font-black font-display text-slate-900 mt-1">
                Your Meal: <span className="text-teal-700">{currentMeal.name}</span>
              </h1>
            </div>

            {/* Portion Control Buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">
                Portion Size:
              </span>
              {[
                { label: '0.5x Half', val: 0.5 },
                { label: '1.0x Standard', val: 1 },
                { label: '1.5x Large', val: 1.5 },
                { label: '2.0x Double', val: 2 }
              ].map(p => (
                <button
                  key={p.val}
                  onClick={() => setPortionMultiplier(p.val)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                    portionMultiplier === p.val
                      ? 'bg-teal-600 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Nutrition Score Banner */}
            <div className="p-4 rounded-2xl bg-gradient-to-r from-teal-50 via-emerald-50 to-teal-50 border border-teal-200/80 flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-teal-600 text-white flex items-center justify-center font-black text-xl shadow-md">
                  {currentMeal.score}
                </div>
                <div>
                  <div className="flex items-center gap-1">
                    <span className="text-sm font-black text-slate-900">Nutrition Score:</span>
                    <span className="text-sm font-black text-teal-700">{currentMeal.score} / 10 ⭐</span>
                  </div>
                  <p className="text-xs text-slate-600">
                    High Nutrient Density • Excellent bioavailable protein & minerals
                  </p>
                </div>
              </div>

              <div className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-extrabold">
                Optimal Quality Fuel
              </div>
            </div>

            {/* Quick Insight Section */}
            <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200/80 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-black text-amber-900 uppercase tracking-wide">
                  Quick AI Insight
                </span>
                <p className="text-sm font-medium text-amber-950 mt-0.5">
                  {currentMeal.insight}
                </p>
              </div>
            </div>

          </div>

        </div>
      </div>

      {/* 4 Circular Visual Progress Meters / Cards (Agent 1 + Agent 2) */}
      <div className="mb-8">
        <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-teal-600" />
          <span>Nutritional Breakdown & Daily Allowances</span>
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
          <CircularProgress
            value={calories}
            max={2000}
            label="Calories"
            unit="kcal"
            color="#0d9488"
            icon={Flame}
          />
          <CircularProgress
            value={protein}
            max={100}
            label="Protein"
            unit="g"
            color="#14b8a6"
            icon={Dumbbell}
          />
          <CircularProgress
            value={carbs}
            max={220}
            label="Carbohydrates"
            unit="g"
            color="#f59e0b"
            icon={Wheat}
          />
          <CircularProgress
            value={fats}
            max={65}
            label="Healthy Fats"
            unit="g"
            color="#f97316"
            icon={Droplet}
          />
          <CircularProgress
            value={fiber}
            max={30}
            label="Dietary Fiber"
            unit="g"
            color="#10b981"
            icon={Leaf}
          />
        </div>
      </div>

      {/* Nutrient Data Table (Exact User Specification) */}
      <div className="bg-white rounded-3xl p-6 border border-teal-100 shadow-card-soft mb-8">
        <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center justify-between">
          <span>Official Nutrient Summary</span>
          <span className="text-xs font-semibold text-slate-400">Values based on {portionMultiplier}x portion</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-teal-100 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Nutrient</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Daily Value (% DV)</th>
                <th className="py-3 px-4">Rating</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              <tr className="hover:bg-teal-50/40 transition-colors">
                <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                  <span>🔥</span> Calories
                </td>
                <td className="py-3.5 px-4 font-black text-slate-800">{calories} kcal</td>
                <td className="py-3.5 px-4 text-slate-600 font-semibold">{Math.round((calories / 2000) * 100)}%</td>
                <td className="py-3.5 px-4">
                  <span className="px-2.5 py-0.5 rounded-full bg-teal-100 text-teal-800 text-xs font-bold">Standard</span>
                </td>
              </tr>

              <tr className="hover:bg-teal-50/40 transition-colors">
                <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                  <span>🥩</span> Protein
                </td>
                <td className="py-3.5 px-4 font-black text-teal-700">{protein} g</td>
                <td className="py-3.5 px-4 text-slate-600 font-semibold">{Math.round((protein / 100) * 100)}%</td>
                <td className="py-3.5 px-4">
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">High</span>
                </td>
              </tr>

              <tr className="hover:bg-teal-50/40 transition-colors">
                <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                  <span>🍚</span> Carbohydrates
                </td>
                <td className="py-3.5 px-4 font-black text-amber-700">{carbs} g</td>
                <td className="py-3.5 px-4 text-slate-600 font-semibold">{Math.round((carbs / 220) * 100)}%</td>
                <td className="py-3.5 px-4">
                  <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 text-xs font-bold">Moderate-High</span>
                </td>
              </tr>

              <tr className="hover:bg-teal-50/40 transition-colors">
                <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                  <span>🧈</span> Fats
                </td>
                <td className="py-3.5 px-4 font-black text-slate-800">{fats} g</td>
                <td className="py-3.5 px-4 text-slate-600 font-semibold">{Math.round((fats / 65) * 100)}%</td>
                <td className="py-3.5 px-4">
                  <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-bold">Balanced</span>
                </td>
              </tr>

              <tr className="hover:bg-teal-50/40 transition-colors">
                <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                  <span>🌾</span> Dietary Fiber
                </td>
                <td className="py-3.5 px-4 font-black text-emerald-700">{fiber} g</td>
                <td className="py-3.5 px-4 text-slate-600 font-semibold">{Math.round((fiber / 30) * 100)}%</td>
                <td className="py-3.5 px-4">
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">Good</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Action Footer Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-teal-100 shadow-card-soft">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center font-bold">
            🥗
          </div>
          <div>
            <p className="font-bold text-slate-800 text-sm">Satisfied with this analysis?</p>
            <p className="text-xs text-slate-500">Log this meal to monitor your 2,000 kcal daily budget</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <motion.button
            variants={popButtonVariants}
            initial="initial"
            whileHover="hover"
            whileTap="tap"
            onClick={handleLogToDaily}
            disabled={hasLogged}
            className={`btn-pop flex items-center gap-2 px-6 py-3 rounded-full font-bold text-sm shadow-pop cursor-pointer ${
              hasLogged
                ? 'bg-emerald-600 text-white cursor-default'
                : 'bg-gradient-to-r from-teal-600 to-teal-500 text-white'
            }`}
          >
            {hasLogged ? (
              <>
                <CheckCircle className="w-4 h-4 text-white" />
                <span>Logged to Today's Dashboard!</span>
              </>
            ) : (
              <>
                <PlusCircle className="w-4 h-4 text-teal-100" />
                <span>Log to Today's Dashboard</span>
              </>
            )}
          </motion.button>

          {hasLogged && (
            <button
              onClick={onNavigateToDashboard}
              className="px-5 py-3 rounded-full bg-teal-50 text-teal-700 hover:bg-teal-100 font-bold text-sm border border-teal-200 transition-colors"
            >
              View Daily Dashboard →
            </button>
          )}
        </div>
      </div>

    </div>
  );
}
