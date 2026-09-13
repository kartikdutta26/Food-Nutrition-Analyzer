import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  User, 
  Target, 
  Flame, 
  Dumbbell, 
  Droplet, 
  Save, 
  Check, 
  Activity, 
  Sparkles,
  Sliders
} from 'lucide-react';
import { popButtonVariants } from '../animations/motionVariants';

export default function ProfileSettings({ userProfile, onUpdateProfile }) {
  const [formData, setFormData] = useState({ ...userProfile });
  const [savedSuccess, setSavedSuccess] = useState(false);

  // When goal changes, auto-recalculate recommended targets
  const handleGoalSelect = (goalName) => {
    let newTargets = { ...formData.targets };
    if (goalName === 'Gain Muscle') {
      newTargets = { calories: 2400, protein: 140, carbs: 260, fats: 70, water: 3.0 };
    } else if (goalName === 'Maintain Weight') {
      newTargets = { calories: 2000, protein: 100, carbs: 220, fats: 65, water: 2.5 };
    } else if (goalName === 'Lose Weight') {
      newTargets = { calories: 1750, protein: 115, carbs: 160, fats: 50, water: 2.8 };
    }

    setFormData({
      ...formData,
      goal: goalName,
      targets: newTargets
    });
  };

  const handleSave = (e) => {
    e.preventDefault();
    onUpdateProfile(formData);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const goals = [
    { id: 'Gain Muscle', title: 'Gain Muscle', icon: '🏋️', desc: 'Higher protein & caloric surplus for hypertrophy' },
    { id: 'Maintain Weight', title: 'Maintain Weight', icon: '⚖️', desc: 'Balanced energy expenditure & metabolic stability' },
    { id: 'Lose Weight', title: 'Lose Weight', icon: '🔥', desc: 'Mild caloric deficit preserving lean tissue' }
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      
      {/* Header */}
      <div className="text-center max-w-xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold uppercase tracking-wider mb-2">
          <User className="w-3.5 h-3.5 text-teal-600" />
          <span>Profile & Biometric Preferences</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-black font-display text-slate-900 tracking-tight">
          Personal Nutrition Profile
        </h2>
        <p className="text-slate-600 text-sm mt-1">
          Customize your biometrics, daily expenditure, and nutrition targets.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Form: Name, Age, Height, Weight, Activity */}
        <div className="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft">
          <form onSubmit={handleSave} className="space-y-6">
            
            <div className="border-b border-slate-100 pb-4">
              <h3 className="font-bold text-slate-900 text-base">Biometrics</h3>
              <p className="text-xs text-slate-500">Used by AI to calibrate basal metabolic rate (BMR).</p>
            </div>

            {/* Name & Age */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1.5">
                  Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1.5">
                  Age
                </label>
                <input
                  type="number"
                  value={formData.age}
                  onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                />
              </div>
            </div>

            {/* Height & Weight */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1.5">
                  Height (cm)
                </label>
                <input
                  type="number"
                  value={formData.height}
                  onChange={(e) => setFormData({ ...formData, height: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1.5">
                  Weight (kg)
                </label>
                <input
                  type="number"
                  value={formData.weight}
                  onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
                />
              </div>
            </div>

            {/* Activity Level */}
            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1.5">
                Activity Level
              </label>
              <select
                value={formData.activityLevel}
                onChange={(e) => setFormData({ ...formData, activityLevel: e.target.value })}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm font-medium"
              >
                <option value="Sedentary">Sedentary (Little or no exercise, desk job)</option>
                <option value="Light">Lightly Active (Light exercise 1-3 days/week)</option>
                <option value="Moderate">Moderately Active (Moderate exercise 3-5 days/week)</option>
                <option value="Active">Very Active (Hard training 6-7 days/week)</option>
              </select>
            </div>

            {/* Goal Selector */}
            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-2">
                Primary Fitness Goal
              </label>
              <div className="space-y-2.5">
                {goals.map((g) => {
                  const isSelected = formData.goal === g.id;
                  return (
                    <div
                      key={g.id}
                      onClick={() => handleGoalSelect(g.id)}
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                        isSelected
                          ? 'border-teal-600 bg-teal-50/80 ring-2 ring-teal-500/20 shadow-sm'
                          : 'border-slate-200 hover:border-teal-200 bg-white'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{g.icon}</span>
                        <div>
                          <p className="font-bold text-slate-900 text-sm">{g.title}</p>
                          <p className="text-xs text-slate-500">{g.desc}</p>
                        </div>
                      </div>

                      {isSelected && (
                        <div className="w-5 h-5 rounded-full bg-teal-600 text-white flex items-center justify-center text-xs">
                          <Check className="w-3.5 h-3.5 stroke-[3]" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Save Button */}
            <motion.button
              variants={popButtonVariants}
              initial="initial"
              whileHover="hover"
              whileTap="tap"
              type="submit"
              className="w-full btn-pop flex items-center justify-center gap-2 py-3.5 rounded-2xl bg-teal-600 text-white font-bold text-sm shadow-pop cursor-pointer"
            >
              {savedSuccess ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Preferences Saved!</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>Save Profile & Recalculate</span>
                </>
              )}
            </motion.button>
          </form>
        </div>

        {/* Right Card: User-Requested "Your Daily Target" Display */}
        <div className="lg:col-span-5 space-y-6">
          
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
              <div>
                <span className="text-xs font-black text-teal-700 uppercase tracking-wider">
                  Calculated by NutriAI
                </span>
                <h3 className="text-xl font-black font-display text-slate-900 mt-0.5">
                  Your Daily Target
                </h3>
              </div>
              <div className="w-10 h-10 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center">
                <Target className="w-5 h-5" />
              </div>
            </div>

            {/* 3 Explicit User Targets */}
            <div className="space-y-4">
              
              {/* Calories: 2,000 kcal */}
              <div className="p-4 rounded-2xl bg-teal-50/60 border border-teal-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold">
                    <Flame className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-500 uppercase">Daily Energy</span>
                    <h4 className="text-sm font-black text-slate-800">Calories</h4>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xl font-black text-slate-900">{formData.targets.calories.toLocaleString()}</span>
                  <span className="text-xs font-semibold text-slate-500 ml-1">kcal</span>
                </div>
              </div>

              {/* Protein: 100 g */}
              <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold">
                    <Dumbbell className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-500 uppercase">Building Block</span>
                    <h4 className="text-sm font-black text-slate-800">Protein</h4>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xl font-black text-emerald-800">{formData.targets.protein}</span>
                  <span className="text-xs font-semibold text-slate-500 ml-1">g</span>
                </div>
              </div>

              {/* Water: 2.5 L */}
              <div className="p-4 rounded-2xl bg-cyan-50/60 border border-cyan-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-cyan-600 text-white flex items-center justify-center font-bold">
                    <Droplet className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-500 uppercase">Hydration</span>
                    <h4 className="text-sm font-black text-slate-800">Water</h4>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xl font-black text-cyan-800">{formData.targets.water}</span>
                  <span className="text-xs font-semibold text-slate-500 ml-1">L</span>
                </div>
              </div>

            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 text-xs text-slate-500 text-center">
              Active Goal: <span className="font-bold text-teal-800">{formData.goal}</span>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
