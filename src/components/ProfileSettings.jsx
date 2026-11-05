import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Check,
  Droplet,
  Dumbbell,
  Flame,
  Save,
  Target,
  User,
} from 'lucide-react';
import { popButtonVariants } from '../animations/motionVariants';
import { validateNutritionTargets } from '../utils/nutritionTargets';

const targetDraftFromProfile = (targets) => ({
  calories: targets?.calories ?? '',
  protein: targets?.protein ?? '',
  carbs: targets?.carbs ?? '',
  fats: targets?.fats ?? '',
});

export default function ProfileSettings({
  userProfile,
  onUpdateProfile,
  isLoading = false,
  isLoaded = false,
  loadError = '',
  actionError = '',
  isSaving = false,
  onRetry,
}) {
  const [formData, setFormData] = useState(() => ({
    ...userProfile,
    targets: targetDraftFromProfile(userProfile.targets),
  }));
  const [dietaryPreferencesText, setDietaryPreferencesText] = useState((userProfile.dietary_preferences || []).join(', '));
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [formValidationError, setFormValidationError] = useState('');

  useEffect(() => {
    setFormData({
      ...userProfile,
      targets: targetDraftFromProfile(userProfile.targets),
    });
    setDietaryPreferencesText((userProfile.dietary_preferences || []).join(', '));
  }, [userProfile]);

  const handleGoalSelect = (goalName) => {
    setFormData((previous) => ({ ...previous, goal: goalName }));
  };

  const handleSave = async (event) => {
    event.preventDefault();
    const dietary_preferences = dietaryPreferencesText.split(',').map((value) => value.trim()).filter(Boolean);
    if (dietary_preferences.length > 30) {
      setFormValidationError('Enter no more than 30 dietary preference labels.');
      return;
    }
    if (dietary_preferences.some((value) => value.length > 80)) {
      setFormValidationError('Each dietary preference must be 80 characters or fewer.');
      return;
    }
    const hasAnyMacroTarget = ['calories', 'protein', 'carbs', 'fats']
      .some((key) => formData.targets[key] !== '' && formData.targets[key] !== null);
    if (hasAnyMacroTarget) {
      const targetError = validateNutritionTargets(formData.targets);
      if (targetError) {
        setFormValidationError(`Daily ${targetError}`);
        return;
      }
    }
    setFormValidationError('');
    const updated = await onUpdateProfile({
      ...formData,
      dietary_preferences,
    });
    if (updated) {
      setSavedSuccess(true);
      window.setTimeout(() => setSavedSuccess(false), 2500);
    }
  };

  const goals = [
    { id: 'Gain Muscle', title: 'Gain Muscle', icon: '🏋️', desc: 'A saved personal preference' },
    { id: 'Maintain Weight', title: 'Maintain Weight', icon: '⚖️', desc: 'A saved personal preference' },
    { id: 'Lose Weight', title: 'Lose Weight', icon: '🔥', desc: 'A saved personal preference' },
  ];

  const targetFields = [
    { key: 'calories', label: 'Calories', unit: 'kcal', Icon: Flame, color: 'teal' },
    { key: 'protein', label: 'Protein', unit: 'g', Icon: Dumbbell, color: 'emerald' },
    { key: 'carbs', label: 'Carbohydrates', unit: 'g', Icon: Activity, color: 'amber' },
    { key: 'fats', label: 'Fats', unit: 'g', Icon: Droplet, color: 'orange' },
  ];

  const targetCardColors = {
    teal: 'bg-teal-50/60 border-teal-100 bg-teal-600',
    emerald: 'bg-emerald-50/60 border-emerald-100 bg-emerald-600',
    amber: 'bg-amber-50/60 border-amber-100 bg-amber-500',
    orange: 'bg-orange-50/60 border-orange-100 bg-orange-500',
  };

  const pageHeading = (
    <div className="text-center max-w-xl mx-auto mb-10">
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold uppercase tracking-wider mb-2">
        <User className="w-3.5 h-3.5 text-teal-600" /><span>Profile &amp; Preferences</span>
      </div>
      <h2 className="text-3xl sm:text-4xl font-black font-display text-slate-900 tracking-tight">Personal Nutrition Profile</h2>
      <p className="text-slate-600 text-sm mt-1">Your profile and nutrition preferences are saved to your account.</p>
    </div>
  );

  if (!isLoaded) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        {pageHeading}
        {isLoading && <p role="status" className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">Loading your saved profile…</p>}
        {loadError && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{loadError}</span><button type="button" onClick={onRetry} disabled={isLoading} className="font-bold underline disabled:opacity-50">Retry</button></div>}
        {!isLoading && !loadError && <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">Your profile is not available yet. Retry to load your account data before editing.</p>}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      {pageHeading}

      {(isLoading || loadError || actionError) && (
        <div className="space-y-2 mb-6" aria-live="polite">
          {isLoading && <p role="status" className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">Loading saved profile…</p>}
          {loadError && <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{loadError}</span><button type="button" onClick={onRetry} disabled={isLoading} className="font-bold underline disabled:opacity-50">Retry</button></div>}
          {actionError && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{actionError}</p>}
        </div>
      )}

      {isLoaded && !userProfile.targets && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 mb-6 text-sm text-amber-900">No daily nutrition targets are configured. You can save your profile now and add targets whenever you are ready.</p>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <div className="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft">
          <form onSubmit={handleSave} className="space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h3 className="font-bold text-slate-900 text-base">Personal details</h3>
              <p className="text-xs text-slate-500">These details are private to your account and sync across your signed-in devices.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div><label className="block text-xs font-bold text-slate-600 uppercase mb-1.5" htmlFor="profile-name">Name</label><input id="profile-name" autoComplete="name" type="text" maxLength="120" value={formData.name ?? ''} onChange={(event) => setFormData({ ...formData, name: event.target.value })} disabled={isLoading || isSaving} className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium" /></div>
              <div><label className="block text-xs font-bold text-slate-600 uppercase mb-1.5" htmlFor="profile-age">Age</label><input id="profile-age" type="number" min="1" max="120" value={formData.age ?? ''} onChange={(event) => setFormData({ ...formData, age: event.target.value })} disabled={isLoading || isSaving} className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium" /></div>
              <div><label className="block text-xs font-bold text-slate-600 uppercase mb-1.5" htmlFor="profile-height">Height (cm)</label><input id="profile-height" type="number" min="30" max="300" step="any" value={formData.height ?? ''} onChange={(event) => setFormData({ ...formData, height: event.target.value })} disabled={isLoading || isSaving} className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium" /></div>
              <div><label className="block text-xs font-bold text-slate-600 uppercase mb-1.5" htmlFor="profile-weight">Weight (kg)</label><input id="profile-weight" type="number" min="0.1" max="700" step="any" value={formData.weight ?? ''} onChange={(event) => setFormData({ ...formData, weight: event.target.value })} disabled={isLoading || isSaving} className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium" /></div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1.5" htmlFor="profile-activity">Activity Level</label>
              <select id="profile-activity" value={formData.activityLevel ?? ''} onChange={(event) => setFormData({ ...formData, activityLevel: event.target.value })} disabled={isLoading || isSaving} className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium">
                <option value="">Select activity level</option>
                <option value="Sedentary">Sedentary (Little or no exercise, desk job)</option><option value="Light">Lightly Active (Light exercise 1-3 days/week)</option><option value="Moderate">Moderately Active (Moderate exercise 3-5 days/week)</option><option value="Active">Very Active (Hard training 6-7 days/week)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-2">Goal preference</label>
              <p className="text-[11px] text-slate-500 mb-2">This preference does not set or calculate nutrition targets.</p>
              <div className="space-y-2.5">
                {goals.map((goal) => {
                  const isSelected = formData.goal === goal.id;
                  return <button type="button" key={goal.id} onClick={() => handleGoalSelect(goal.id)} className={`w-full p-3.5 rounded-2xl border text-left transition-all flex items-center justify-between ${isSelected ? 'border-teal-600 bg-teal-50/80 ring-2 ring-teal-500/20 shadow-sm' : 'border-slate-200 hover:border-teal-200 bg-white'}`}>
                    <span className="flex items-center gap-3"><span className="text-2xl">{goal.icon}</span><span><span className="block font-bold text-slate-900 text-sm">{goal.title}</span><span className="block text-xs text-slate-500">{goal.desc}</span></span></span>
                    {isSelected && <span className="w-5 h-5 rounded-full bg-teal-600 text-white flex items-center justify-center"><Check className="w-3.5 h-3.5 stroke-[3]" /></span>}
                  </button>;
                })}
              </div>
            </div>

            <div>
              <label htmlFor="dietary-preferences" className="block text-xs font-bold text-slate-600 uppercase mb-1.5">Dietary Preferences <span className="font-normal normal-case text-slate-400">(saved)</span></label>
              <textarea id="dietary-preferences" value={dietaryPreferencesText} onChange={(event) => { setDietaryPreferencesText(event.target.value); setFormValidationError(''); }} maxLength={2500} rows={3} placeholder="Vegetarian, dairy-free, gluten-free" className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium" />
              <p className="text-[11px] text-slate-500 mt-1">Separate labels with commas (up to 30 preferences, each up to 80 characters).</p>
            </div>
            {formValidationError && <p role="alert" className="text-sm text-rose-700">{formValidationError}</p>}

            <motion.button variants={popButtonVariants} initial="initial" whileHover="hover" whileTap="tap" type="submit" disabled={!isLoaded || isLoading || isSaving} className="w-full btn-pop flex items-center justify-center gap-2 py-3.5 rounded-2xl bg-teal-600 text-white font-bold text-sm shadow-pop cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
              {savedSuccess ? <><Check className="w-4 h-4" /><span>Profile Saved!</span></> : <><Save className="w-4 h-4" /><span>{isSaving ? 'Saving…' : 'Save Profile & Targets'}</span></>}
            </motion.button>
          </form>
        </div>

        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
              <div><span className="text-xs font-black text-teal-700 uppercase tracking-wider">Backend profile fields</span><h3 className="text-xl font-black font-display text-slate-900 mt-0.5">Daily Nutrition Targets</h3></div>
              <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center"><Target className="w-5 h-5" /></div>
            </div>
            <div className="space-y-3">
              {targetFields.map(({ key, label, unit, Icon, color }) => {
                const colorClasses = targetCardColors[color].split(' ');
                return <div key={key} className={`p-3.5 rounded-2xl ${colorClasses[0]} border ${colorClasses[1]} flex items-center justify-between gap-3`}>
                  <div className="flex items-center gap-3"><div className={`w-9 h-9 rounded-xl ${colorClasses[2]} text-white flex items-center justify-center`}><Icon className="w-4 h-4" /></div><div><span className="text-xs font-bold text-slate-500 uppercase">Daily target</span><h4 className="text-sm font-black text-slate-800">{label}</h4></div></div>
                  <div className="flex items-center gap-2"><input type="number" min="0" max={key === 'calories' ? '100000' : '10000'} step="any" disabled={!isLoaded || isLoading || isSaving} value={formData.targets?.[key] ?? ''} onChange={(event) => { setFormData({ ...formData, targets: { ...formData.targets, [key]: event.target.value } }); setFormValidationError(''); }} aria-label={`${label} daily target`} className="w-24 px-2 py-2 rounded-lg border border-white/80 bg-white text-right text-sm font-black text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100 disabled:text-slate-400" /><span className="text-xs font-semibold text-slate-500">{unit}</span></div>
                </div>;
              })}
            </div>

            <div className="mt-4 p-3.5 rounded-2xl bg-cyan-50/60 border border-cyan-100 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3"><div className="w-9 h-9 rounded-xl bg-cyan-600 text-white flex items-center justify-center"><Droplet className="w-4 h-4" /></div><div><span className="text-xs font-bold text-slate-500 uppercase">Saved profile field</span><h4 className="text-sm font-black text-slate-800">Water target</h4></div></div>
              <div className="flex items-center gap-2"><input type="number" min="0" max="20" step="0.1" value={formData.waterTarget ?? ''} onChange={(event) => setFormData({ ...formData, waterTarget: event.target.value })} disabled={isLoading || isSaving} aria-label="Water target" className="w-24 px-2 py-2 rounded-lg border border-white/80 bg-white text-right text-sm font-black text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500" /><span className="text-xs font-semibold text-slate-500">L</span></div>
            </div>
            <p className="mt-4 text-[11px] text-slate-500 text-center">Goal and water target are stored as profile preferences. Daily macro targets remain separate and continue to power nutrition progress.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
