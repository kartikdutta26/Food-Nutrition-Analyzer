import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Camera, 
  Sparkles, 
  Brain, 
  BarChart3, 
  Target, 
  Flame, 
  Wheat, 
  Dumbbell, 
  ArrowRight,
  Scan,
  CheckCircle2,
  Eye
} from 'lucide-react';
import { 
  popButtonVariants, 
  headingContainer, 
  headingLetter, 
  fadeInUp,
  cardStagger,
  cardItem,
  floatKeyframes,
  floatingBadge
} from '../animations/motionVariants';

export default function HeroLanding({ onNavigateToAnalyzer, onNavigateToDaily }) {
  const brandName = "NutriAI";
  const subHeadline = "Your food. Your goals. One intelligent nutrition agent.";

  // High-res food imagery matching the reference layout
  const primaryFoodImage = "https://images.unsplash.com/photo-1511690656952-34342bb7c2f2?auto=format&fit=crop&w=1600&q=85";
  const referenceDirectImage = "/reference_hero.jpg";
  const [useOriginalReference, setUseOriginalReference] = useState(false);

  const featureCards = [
    {
      id: 'coach',
      icon: Brain,
      title: 'AI Nutrition Coach',
      desc: 'Dietary feedback tailored to your metabolic rate and goals.',
      color: 'from-teal-500/15 to-emerald-500/10',
      accent: 'text-teal-700'
    },
    {
      id: 'analysis',
      icon: BarChart3,
      title: 'Smart Meal Analysis',
      desc: 'Instant computer-vision breakdown of macros, micros, and GI.',
      color: 'from-emerald-500/15 to-teal-500/10',
      accent: 'text-emerald-700'
    },
    {
      id: 'goals',
      icon: Target,
      title: 'Goal-Based Planning',
      desc: 'Dynamic calorie & protein targets for muscle gain or fat loss.',
      color: 'from-teal-500/15 to-cyan-500/10',
      accent: 'text-teal-700'
    },
    {
      id: 'indian-food',
      icon: '🇮🇳',
      isEmoji: true,
      title: 'Indian Food Intelligence',
      desc: 'Trained on 4,500+ dishes: dosas, thalis, dals, rotis & paneer.',
      color: 'from-teal-500/15 to-emerald-500/10',
      accent: 'text-teal-800'
    }
  ];

  return (
    <section className="relative w-full min-h-[calc(100vh-5rem)] flex flex-col justify-between overflow-hidden bg-white">
      
      {/* Decorative ambient background blurs on text side */}
      <div className="absolute top-10 left-10 w-96 h-96 rounded-full bg-teal-100/40 blur-3xl pointer-events-none z-0" />
      <div className="absolute bottom-20 left-1/4 w-80 h-80 rounded-full bg-emerald-50/50 blur-3xl pointer-events-none z-0" />

      {/* Main Container */}
      <div className="relative w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12 z-20 flex-grow flex items-center">
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          
          {/* ========================================================= */}
          {/* LEFT HALF: Website Text Part (Clean White, Headings, CTAs) */}
          {/* ========================================================= */}
          <div className="lg:col-span-7 xl:col-span-6 z-20 space-y-6 pr-0 lg:pr-6">
            
            {/* Pill Badge */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-50 border border-teal-200/90 text-teal-800 text-xs font-bold uppercase tracking-wider shadow-sm w-fit"
            >
              <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
              <span>Intelligent Nutrition Agent</span>
              <span className="text-teal-300">|</span>
              <span className="text-teal-600 font-semibold normal-case">Know what's on your plate</span>
            </motion.div>

            {/* Arriving Headline with Agent 1 animated letter & word reveal */}
            <div>
              <motion.h1
                variants={headingContainer}
                initial="hidden"
                animate="visible"
                className="text-5xl sm:text-6xl xl:text-7xl font-black font-display tracking-tight text-slate-900 leading-[1.06]"
              >
                <span className="inline-flex overflow-hidden">
                  {brandName.split("").map((char, index) => (
                    <motion.span
                      key={`char-${index}`}
                      variants={headingLetter}
                      className={index >= 5 ? "text-teal-600 inline-block" : "text-slate-900 inline-block"}
                    >
                      {char}
                    </motion.span>
                  ))}
                </span>
                <motion.span 
                  className="inline-block ml-3 text-4xl align-middle"
                  animate={{ rotate: [0, 14, -8, 0] }}
                  transition={{ duration: 3, repeat: Infinity, repeatDelay: 2 }}
                >
                  🥗
                </motion.span>
              </motion.h1>

              {/* Sub-headline: "Your food. Your goals. One intelligent nutrition agent." */}
              <motion.p
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.35 }}
                className="text-2xl sm:text-3xl font-bold font-display text-teal-900/90 mt-2.5 tracking-tight leading-snug"
              >
                {subHeadline}
              </motion.p>
            </div>

            {/* Small Description */}
            <motion.p
              variants={fadeInUp}
              initial="hidden"
              animate="visible"
              transition={{ delay: 0.45 }}
              className="text-base sm:text-lg text-slate-600 font-normal leading-relaxed max-w-xl"
            >
              Snap your meal. Understand what’s on your plate. Let AI help you decide what to eat next.
            </motion.p>

            {/* Two Buttons with Pop Up Effect */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.55 }}
              className="flex flex-wrap items-center gap-4 pt-1"
            >
              {/* Button 1: 📸 Analyze My Meal */}
              <motion.button
                variants={popButtonVariants}
                initial="initial"
                whileHover="hover"
                whileTap="tap"
                onClick={onNavigateToAnalyzer}
                className="btn-pop flex items-center justify-center gap-3 px-8 py-4 rounded-full bg-gradient-to-r from-teal-600 via-teal-500 to-teal-600 bg-[length:200%_auto] text-white font-bold text-base tracking-wide shadow-pop cursor-pointer"
              >
                <Camera className="w-5 h-5 text-teal-100 animate-pulse" />
                <span>📸 Analyze My Meal</span>
                <ArrowRight className="w-4 h-4 opacity-90" />
              </motion.button>

              {/* Button 2: ✨ Start My Nutrition Journey */}
              <motion.button
                variants={popButtonVariants}
                initial="initial"
                whileHover="hover"
                whileTap="tap"
                onClick={onNavigateToDaily}
                className="btn-pop-white flex items-center justify-center gap-2.5 px-7 py-4 rounded-full bg-white text-teal-800 border-2 border-teal-200 font-bold text-base tracking-wide shadow-sm hover:border-teal-500 hover:bg-teal-50/60 cursor-pointer"
              >
                <Sparkles className="w-5 h-5 text-teal-600" />
                <span>✨ Start My Nutrition Journey</span>
              </motion.button>
            </motion.div>

            {/* 3-4 Small Feature Cards (Clean & Not Overloaded) */}
            <div className="pt-4">
              <motion.div
                variants={cardStagger}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl"
              >
                {featureCards.map((card) => {
                  const Icon = card.icon;
                  return (
                    <motion.div
                      key={card.id}
                      variants={cardItem}
                      whileHover={{ y: -3, scale: 1.02 }}
                      className="p-3.5 rounded-2xl bg-white border border-teal-100/90 shadow-card-soft hover:border-teal-300 hover:shadow-md transition-all duration-200 flex flex-col justify-between"
                    >
                      <div className="flex items-center gap-2.5 mb-1">
                        <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-base bg-gradient-to-br ${card.color} ${card.accent}`}>
                          {card.isEmoji ? (
                            <span>{card.icon}</span>
                          ) : (
                            <Icon className="w-4 h-4 stroke-[2.2]" />
                          )}
                        </div>
                        <h3 className="font-bold text-slate-800 text-xs sm:text-sm tracking-tight">
                          {card.title}
                        </h3>
                      </div>
                      <p className="text-[11px] text-slate-500 leading-relaxed">
                        {card.desc}
                      </p>
                    </motion.div>
                  );
                })}
              </motion.div>
            </div>

          </div>

          {/* Spacer on desktop for right column */}
          <div className="hidden lg:block lg:col-span-5 xl:col-span-6" />

        </div>
      </div>

      {/* ========================================================================= */}
      {/* RIGHT HALF: FULL-SCREEN DIAGONAL PARTITION COVERING HALF THE SCREEN       */}
      {/* ========================================================================= */}
      <div 
        className="hidden lg:block absolute right-0 top-0 bottom-0 w-[50%] xl:w-[52%] h-full z-10 overflow-hidden diagonal-partition-desktop"
      >
        {/* Crisp High-Res Food Imagery Covering Edge-to-Edge */}
        <div className="relative w-full h-full">
          <img
            src={useOriginalReference ? referenceDirectImage : primaryFoodImage}
            alt="Healthy nutritious food platter with fruits and meals"
            className="w-full h-full object-cover object-center transition-opacity duration-500"
          />

          {/* Gentle teal ambient gradient wash */}
          <div className="absolute inset-0 bg-gradient-to-r from-teal-950/20 via-transparent to-transparent pointer-events-none" />

          {/* Visual Divider Seam Along the Diagonal Line */}
          <div 
            className="absolute top-0 bottom-0 left-0 w-12 bg-gradient-to-r from-teal-900/20 to-transparent pointer-events-none" 
          />

          {/* AI Laser Scan Line sweeping across the diagonal food spread (Agent 1) */}
          <motion.div
            className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-teal-400 to-transparent shadow-[0_0_20px_#14b8a6] opacity-90 pointer-events-none"
            animate={{ top: ['4%', '95%', '4%'] }}
            transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut' }}
          />

          {/* Overlay Floating Paneer Rice Card (Matching User's core Indian dish) */}
          <motion.div
            variants={floatingBadge(0.5, 14)}
            animate="animate"
            onClick={onNavigateToAnalyzer}
            className="absolute bottom-10 left-12 z-30 p-3 rounded-2xl bg-white/95 backdrop-blur-md shadow-2xl border border-teal-100 flex items-center gap-3 cursor-pointer hover:border-teal-400 transition-colors max-w-xs"
          >
            <img
              src="https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=200&q=80"
              alt="Paneer Rice Bowl"
              className="w-14 h-14 rounded-xl object-cover"
            />
            <div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wide">AI Food Vision</span>
              </div>
              <h4 className="text-xs font-black text-slate-900 leading-tight">Paneer Rice Bowl</h4>
              <p className="text-[11px] font-bold text-slate-500 mt-0.5">620 kcal • 28g Protein</p>
            </div>
          </motion.div>

          {/* Floating Macro Highlight Badges (Calories, Protein, Carbs, Fats) */}
          
          {/* 1. Calories Badge */}
          <motion.div
            variants={floatingBadge(0.2, 12)}
            animate="animate"
            className="absolute top-16 left-28 z-30 px-4 py-2.5 rounded-2xl bg-white/95 backdrop-blur-md shadow-xl border border-teal-100 flex items-center gap-2.5"
          >
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
              <Flame className="w-4 h-4 fill-amber-500 text-amber-500" />
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Calories</p>
              <p className="text-xs font-black text-slate-900">620 kcal</p>
            </div>
          </motion.div>

          {/* 2. Protein Badge */}
          <motion.div
            variants={floatingBadge(1.2, 15)}
            animate="animate"
            className="absolute top-48 right-12 z-30 px-4 py-2.5 rounded-2xl bg-white/95 backdrop-blur-md shadow-xl border border-teal-100 flex items-center gap-2.5"
          >
            <div className="w-8 h-8 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center font-bold">
              <Dumbbell className="w-4 h-4" />
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Protein</p>
              <p className="text-xs font-black text-teal-700">28 g <span className="text-[10px] text-slate-400 font-medium">(High)</span></p>
            </div>
          </motion.div>

          {/* 3. Carbs & Fats Highlight Pill */}
          <motion.div
            variants={floatingBadge(0.8, 10)}
            animate="animate"
            className="absolute bottom-36 right-10 z-30 px-4 py-2.5 rounded-2xl bg-teal-950/90 backdrop-blur-md text-white shadow-xl flex items-center gap-3 text-xs font-bold border border-teal-800/60"
          >
            <div className="flex items-center gap-1">
              <Wheat className="w-3.5 h-3.5 text-teal-300" />
              <span>72g Carbs</span>
            </div>
            <span className="text-teal-700">|</span>
            <div className="flex items-center gap-1">
              <span>🧈 22g Fats</span>
            </div>
          </motion.div>

          {/* Toggle button to switch between High-Res Spread and Original Reference */}
          <div className="absolute top-6 right-6 z-30">
            <button
              onClick={() => setUseOriginalReference(!useOriginalReference)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900/80 hover:bg-slate-900 text-white text-[11px] font-medium backdrop-blur-md border border-white/20 shadow-md transition-all cursor-pointer"
              title="Toggle between HD Flatlay and User Reference image"
            >
              <Eye className="w-3.5 h-3.5 text-teal-400" />
              <span>{useOriginalReference ? 'Show HD Flatlay' : 'Show Reference Photo'}</span>
            </button>
          </div>

        </div>
      </div>

      {/* ========================================================================= */}
      {/* MOBILE / TABLET FALLBACK: Diagonal Card under text                        */}
      {/* ========================================================================= */}
      <div className="lg:hidden w-full relative z-20 px-4 pb-8">
        <div className="relative rounded-3xl overflow-hidden shadow-xl border-2 border-teal-200 aspect-[16/10] diagonal-partition-mobile">
          <img
            src={useOriginalReference ? referenceDirectImage : primaryFoodImage}
            alt="Healthy food platter"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-teal-950/60 via-transparent to-transparent" />
          <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-white">
            <div>
              <span className="text-[10px] uppercase font-bold text-teal-300 tracking-wider">AI Vision Demo</span>
              <p className="text-sm font-black">Nutritious Fruit & Meal Flatlay</p>
            </div>
            <button
              onClick={onNavigateToAnalyzer}
              className="px-3 py-1.5 rounded-xl bg-teal-600 text-white text-xs font-bold"
            >
              Scan Food →
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Nutrition Feature Ticker */}
      <div className="w-full bg-teal-900/5 border-t border-teal-100/80 py-3.5 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between text-xs font-medium text-teal-900 gap-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600" />
            <span>98.4% Accuracy on Indian Gravies & Breads</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600" />
            <span>Real-time Macronutrient & Glycemic Indexing</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600" />
            <span>Zero Calorie Estimation Hassle</span>
          </div>
        </div>
      </div>

    </section>
  );
}
