import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  Dumbbell,
  Flame,
  Image as ImageIcon,
  Layers,
  Leaf,
  PlusCircle,
  Sparkles,
  Wheat,
  Droplet,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { popButtonVariants } from '../animations/motionVariants';
import { buildFoodMealRequest } from '../utils/foodLookup';
import { fetchFoodPhoto } from '../api/client';

const nutrients = [
  { key: 'calories', label: 'Calories', unit: 'kcal', icon: Flame, color: '#0d9488', text: 'text-slate-800', symbol: '🔥' },
  { key: 'protein', label: 'Protein', unit: 'g', icon: Dumbbell, color: '#14b8a6', text: 'text-teal-700', symbol: '🥩' },
  { key: 'carbs', label: 'Carbohydrates', unit: 'g', icon: Wheat, color: '#f59e0b', text: 'text-amber-700', symbol: '🍚' },
  { key: 'fats', label: 'Fats', unit: 'g', icon: Droplet, color: '#f97316', text: 'text-slate-800', symbol: '🧈' },
  { key: 'fiber', label: 'Dietary Fiber', unit: 'g', icon: Leaf, color: '#10b981', text: 'text-emerald-700', symbol: '🌾' },
];

const formatAmount = (value) => value == null
  ? 'Not reported'
  : Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });

function CircularProgress({ value, target, label, unit, color, icon: Icon }) {
  const hasValue = value != null && Number.isFinite(Number(value));
  const hasTarget = hasValue && Number.isFinite(Number(target)) && Number(target) > 0;
  const percentage = hasTarget ? Math.min(Math.round((value / Number(target)) * 100), 100) : 0;
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-4 rounded-2xl bg-white border border-teal-100 shadow-card-soft">
      <div className="relative w-24 h-24 flex items-center justify-center">
        <svg className="w-full h-full -rotate-90" aria-hidden="true">
          <circle cx="48" cy="48" r={radius} stroke="#f0fdfa" strokeWidth="8" fill="transparent" />
          <motion.circle
            cx="48" cy="48" r={radius} stroke={color} strokeWidth="8" strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }} animate={{ strokeDashoffset }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }} strokeLinecap="round" fill="transparent"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <Icon className="w-4 h-4 mb-0.5 text-slate-400" />
          <span className="text-base font-black text-slate-900 leading-none">{hasValue ? formatAmount(value) : '—'}</span>
          <span className="text-[10px] text-slate-400 font-semibold">{unit}</span>
        </div>
      </div>
      <div className="mt-2 text-center">
        <span className="text-xs font-bold text-slate-700">{label}</span>
        <div className="text-[10px] text-slate-400 font-medium mt-0.5">
          {!hasValue ? 'Not reported by source' : hasTarget ? `${percentage}% of saved target` : 'No saved target'}
        </div>
      </div>
    </div>
  );
}

export default function NutritionResults({
  meal,
  onLogMeal,
  userTargets,
  profileLoading = false,
  profileError = '',
  onRetryProfile,
  logError = '',
  isLoggingMeal = false,
  onScanAnother,
  onNavigateToDashboard,
}) {
  const [portionMultiplier, setPortionMultiplier] = useState(1);
  const [mealSlot, setMealSlot] = useState('Lunch');
  const [hasLogged, setHasLogged] = useState(false);
  const [photoState, setPhotoState] = useState({ foodName: '', photo: null, loading: false });
  const selectedFoodName = meal?.name?.trim() || '';
  const hasNutrition = Boolean(meal?.nutrition);

  useEffect(() => {
    if (!selectedFoodName || !hasNutrition) {
      setPhotoState({ foodName: selectedFoodName, photo: null, loading: false });
      return undefined;
    }

    const controller = new AbortController();
    let isCurrentSelection = true;
    setPhotoState({ foodName: selectedFoodName, photo: null, loading: true });
    fetchFoodPhoto(selectedFoodName, { signal: controller.signal })
      .then((photo) => {
        if (isCurrentSelection) {
          setPhotoState({ foodName: selectedFoodName, photo, loading: false });
        }
      })
      .catch((error) => {
        if (isCurrentSelection && error?.name !== 'AbortError') {
          setPhotoState({ foodName: selectedFoodName, photo: null, loading: false });
        }
      });

    return () => {
      isCurrentSelection = false;
      controller.abort();
    };
  }, [selectedFoodName, hasNutrition]);

  const selectedPhoto = photoState.foodName === selectedFoodName ? photoState.photo : null;
  const photoLoading = photoState.foodName === selectedFoodName && photoState.loading;

  const handlePhotoError = () => {
    setPhotoState((current) => current.foodName === selectedFoodName
      ? { foodName: selectedFoodName, photo: null, loading: false }
      : current);
  };

  if (!meal?.nutrition) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        <div className="bg-white rounded-3xl p-8 border border-teal-100 shadow-card-soft text-center">
          <h2 className="text-2xl font-black text-slate-900">No food analysis to display</h2>
          <p className="text-sm text-slate-600 mt-2">Enter a food name to look up USDA nutrition data or a sample preset.</p>
          <button onClick={onScanAnother} className="mt-5 px-5 py-3 rounded-full bg-teal-600 text-white font-bold text-sm">Analyze a food</button>
        </div>
      </div>
    );
  }

  const nutrition = meal.nutrition;
  const amounts = Object.fromEntries(nutrients.map(({ key }) => (
    [key, nutrition[key] == null ? null : Number((Number(nutrition[key]) * portionMultiplier).toFixed(1))]
  )));
  const isSample = meal.data_source === 'sample_preset';
  const isUSDA = meal.data_source === 'usda_food_data_central';
  const sourceLabel = isUSDA ? 'USDA FoodData Central' : isSample ? 'Sample preset' : 'Backend response';

  const handleLogToDaily = async () => {
    const request = buildFoodMealRequest(meal, mealSlot, amounts, portionMultiplier);
    if (!request) return;
    const saved = await onLogMeal(request);
    if (!saved) return;
    setHasLogged(true);
    confetti({ particleCount: 65, spread: 65, origin: { y: 0.7 }, colors: ['#0d9488', '#14b8a6', '#5eead4', '#10b981', '#f59e0b'] });
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <button onClick={onScanAnother} className="flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-teal-700 transition-colors cursor-pointer">
          <ArrowLeft className="w-4 h-4" /><span>Analyze Another Meal</span>
        </button>
        <div className="flex items-center gap-2 text-xs font-semibold text-teal-800 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-200">
          <Sparkles className="w-3.5 h-3.5 text-teal-600" /><span>{isUSDA ? 'USDA FoodData Central' : 'Backend food response'}</span>
        </div>
      </div>

      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft mb-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
          <div className="md:col-span-4 relative rounded-2xl overflow-hidden aspect-square border border-teal-200 shadow-md bg-gradient-to-br from-teal-50 to-emerald-100 flex items-center justify-center">
            {selectedPhoto?.image_url ? (
              <>
                <img
                  src={selectedPhoto.image_url}
                  alt={`Photograph related to ${meal.name}`}
                  className="absolute inset-0 h-full w-full object-cover"
                  onError={handlePhotoError}
                />
                <div className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-slate-900/80 text-white text-[11px] font-bold">Unsplash photo</div>
              </>
            ) : (
              <div role="img" aria-label={`Food photo unavailable for ${meal.name}`} className="text-center p-5">
                <div className="mx-auto mb-3 flex h-20 w-20 items-center justify-center rounded-3xl border border-white/80 bg-white/60 text-teal-600 shadow-sm">
                  <ImageIcon className="h-10 w-10" aria-hidden="true" />
                </div>
                <span className="block text-sm font-bold text-teal-900">
                  {photoLoading ? 'Finding a food photo…' : 'Food photo unavailable'}
                </span>
                <span className="mt-1 block text-xs text-slate-600">
                  {photoLoading ? 'Searching Unsplash for a related photograph.' : 'Nutrition lookup does not include a food photo.'}
                </span>
              </div>
            )}
          </div>

          <div className="md:col-span-8 space-y-4">
            <div>
              <span className="text-xs font-extrabold uppercase tracking-wider text-teal-700">{isSample ? 'Sample preset nutrition' : 'USDA nutrition lookup'}</span>
              <h1 className="text-3xl sm:text-4xl font-black font-display text-slate-900 mt-1">
                Food: <span className="text-teal-700">{meal.name}</span>
              </h1>
              {selectedPhoto && (
                <p className="text-xs text-slate-500 mt-2">
                  Photo by{' '}
                  <a href={selectedPhoto.photographer_profile_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-teal-700 underline">
                    {selectedPhoto.photographer_name}
                  </a>{' '}on{' '}
                  <a href={selectedPhoto.attribution_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-teal-700 underline">
                    Unsplash
                  </a>
                </p>
              )}
              {meal.preset_id ? (
                <p className="text-sm text-slate-500 mt-1">Preset ID: <span className="font-semibold">{meal.preset_id}</span></p>
              ) : (
                <p className="text-sm text-slate-500 mt-1">FoodData Central ID: <span className="font-semibold">{meal.fdc_id}</span></p>
              )}
              {meal.serving && <p className="text-sm text-slate-500 mt-1">Serving: <span className="font-semibold">{meal.serving.description}</span></p>}
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Preview portion:</span>
              {[
                { label: '0.5x Half', val: 0.5 },
                { label: '1.0x Standard', val: 1 },
                { label: '1.5x Large', val: 1.5 },
                { label: '2.0x Double', val: 2 },
              ].map(({ label, val }) => (
                <button key={val} onClick={() => setPortionMultiplier(val)} className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${portionMultiplier === val ? 'bg-teal-600 text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                  {label}
                </button>
              ))}
            </div>

            <div className="p-4 rounded-2xl bg-gradient-to-r from-teal-50 via-emerald-50 to-teal-50 border border-teal-200/80">
              <div className="flex items-start gap-3">
                <InfoIcon />
                <div>
                  <p className="text-sm font-black text-slate-900">{isSample ? 'Temporary sample data' : 'Nutrition source'}</p>
                  <p className="text-xs text-slate-600 mt-1">{meal.notice || (isSample ? 'These values are for demonstration only and are not verified nutrition data or AI analysis.' : 'Nutrition supplied by the backend.')}</p>
                </div>
              </div>
            </div>

            {portionMultiplier !== 1 && (
              <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
                {isSample
                  ? 'Scaled preview calculated from sample values. Return to the standard serving before logging this preset.'
                  : 'Nutrition values are scaled from the USDA serving shown above. This adjusted serving will be logged.'}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-teal-600" /><span>Nutrition values per serving</span>
        </h3>
        {profileLoading && <p role="status" className="mb-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">Loading saved targets for comparison…</p>}
        {profileError && <div role="alert" className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>Saved targets could not be loaded: {profileError}</span><button type="button" onClick={onRetryProfile} disabled={profileLoading} className="font-bold underline disabled:opacity-50">Retry</button></div>}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
          {nutrients.map(({ key, label, unit, icon, color }) => (
            <CircularProgress key={key} value={amounts[key]} target={key === 'fiber' ? null : userTargets?.[key]} label={label} unit={unit} color={color} icon={icon} />
          ))}
        </div>
      </div>

      <div className="bg-white rounded-3xl p-6 border border-teal-100 shadow-card-soft mb-8">
        <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center justify-between gap-3">
          <span>Nutrition summary</span>
          <span className="text-xs font-semibold text-slate-400">{portionMultiplier}x preview • {sourceLabel}</span>
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-teal-100 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Nutrient</th><th className="py-3 px-4">Amount</th><th className="py-3 px-4">Progress against saved target</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {nutrients.map(({ key, label, unit, text, symbol }) => {
                const target = key === 'fiber' ? null : userTargets?.[key];
                const hasTarget = Number.isFinite(Number(target)) && Number(target) > 0;
                const progress = amounts[key] == null
                  ? 'Not reported by source'
                  : hasTarget
                    ? `${Math.round((amounts[key] / Number(target)) * 100)}%`
                    : key === 'fiber' ? 'No backend target' : 'Target not loaded';
                return (
                  <tr key={key} className="hover:bg-teal-50/40 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-slate-900"><span className="mr-2">{symbol}</span>{label}</td>
                    <td className={`py-3.5 px-4 font-black ${text}`}>{formatAmount(amounts[key])} {unit}</td>
                    <td className="py-3.5 px-4 text-slate-600 font-semibold">{progress}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-teal-100 shadow-card-soft">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center font-bold">🥗</div>
          <div>
            <p className="font-bold text-slate-800 text-sm">Add this food to your meal log?</p>
            <p className="text-xs text-slate-500">{isSample ? 'The backend stores the standard sample preset serving.' : `The backend stores ${portionMultiplier}× ${meal.serving?.description || 'the USDA serving'} with its USDA source and food ID.`}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="sr-only" htmlFor="analysis-meal-slot">Meal slot</label>
          <select id="analysis-meal-slot" value={mealSlot} onChange={(event) => setMealSlot(event.target.value)} disabled={hasLogged || isLoggingMeal} className="px-3 py-2.5 rounded-xl border border-slate-200 text-xs font-bold text-slate-700">
            <option value="Breakfast">Breakfast</option><option value="Lunch">Lunch</option><option value="Dinner">Dinner</option><option value="Snack">Snack</option>
          </select>
          <motion.button
            variants={popButtonVariants} initial="initial" whileHover="hover" whileTap="tap"
            onClick={handleLogToDaily}
            disabled={hasLogged || isLoggingMeal || (isSample && portionMultiplier !== 1)}
            className={`btn-pop flex items-center gap-2 px-6 py-3 rounded-full font-bold text-sm shadow-pop cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${hasLogged ? 'bg-emerald-600 text-white' : 'bg-gradient-to-r from-teal-600 to-teal-500 text-white'}`}
          >
            {hasLogged ? <><CheckCircle className="w-4 h-4" /><span>Logged to Daily Nutrition</span></> : <><PlusCircle className="w-4 h-4 text-teal-100" /><span>{isLoggingMeal ? 'Saving…' : isUSDA ? 'Log This Serving' : 'Log Standard Serving'}</span></>}
          </motion.button>
          {hasLogged && <button onClick={onNavigateToDashboard} className="px-5 py-3 rounded-full bg-teal-50 text-teal-700 hover:bg-teal-100 font-bold text-sm border border-teal-200 transition-colors">View Daily Nutrition →</button>}
        </div>
      </div>
      {isSample && portionMultiplier !== 1 && <p className="mt-3 text-right text-xs text-slate-500">Choose 1.0x Standard to log the backend preset serving.</p>}
      {logError && <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 flex items-start gap-2"><AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />{logError}</p>}
    </div>
  );
}

function InfoIcon() {
  return <Sparkles className="w-5 h-5 text-teal-600 shrink-0 mt-0.5" />;
}
