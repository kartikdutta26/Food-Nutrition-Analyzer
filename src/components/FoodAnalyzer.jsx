import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  UploadCloud, 
  Camera, 
  Keyboard, 
  Sparkles, 
  Check, 
  Image as ImageIcon, 
  RefreshCw, 
  Scan, 
  Search, 
  ArrowRight,
  Flame,
  Zap,
  Info
} from 'lucide-react';
import { popButtonVariants, scannerBeamVariants } from '../animations/motionVariants';
import { PRESET_MEALS } from '../data/mockMeals';

export default function FoodAnalyzer({ onAnalysisComplete }) {
  // 3 Modes: 'upload', 'camera', 'manual'
  const [activeMode, setActiveMode] = useState('upload');
  const [selectedMeal, setSelectedMeal] = useState(PRESET_MEALS[0]); // Default: Paneer Rice Bowl
  const [customImage, setCustomImage] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState('');
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraCountdown, setCameraCountdown] = useState(null);
  const fileInputRef = useRef(null);

  // Handle local image file upload
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setCustomImage(event.target?.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // Simulate Camera snapshot
  const triggerCameraSnap = () => {
    setCameraCountdown(3);
    const interval = setInterval(() => {
      setCameraCountdown((prev) => {
        if (prev === 1) {
          clearInterval(interval);
          setCameraCountdown(null);
          setCameraActive(false);
          // Set to captured meal
          setCustomImage('https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80');
          return null;
        }
        return prev ? prev - 1 : null;
      });
    }, 800);
  };

  // Trigger analysis simulation
  const handleAnalyze = () => {
    setIsScanning(true);
    setScanStep('Detecting food segments...');

    setTimeout(() => {
      setScanStep('Classifying ingredients & portion weights...');
    }, 700);

    setTimeout(() => {
      setScanStep('Computing caloric density & amino acid profiles...');
    }, 1400);

    setTimeout(() => {
      setIsScanning(false);
      // Pass the selected meal (or custom data) to results
      const mealToDeliver = {
        ...selectedMeal,
        image: customImage || selectedMeal.image,
      };
      onAnalysisComplete(mealToDeliver);
    }, 2100);
  };

  // Filter meals for manual entry
  const filteredMeals = PRESET_MEALS.filter(m => 
    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold uppercase tracking-wider mb-3">
          <Sparkles className="w-3.5 h-3.5 text-teal-600" />
          <span>Core Feature • Multimodal AI</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-black font-display text-slate-900 tracking-tight">
          Analyze Your Meal
        </h2>
        <p className="text-slate-600 mt-2 text-base">
          Upload a picture of your food to get instant nutritional information, glycemic index, and AI coach insights.
        </p>
      </div>

      {/* 3 Entry Modes Navigation */}
      <div className="flex justify-center mb-8">
        <div className="inline-flex p-1.5 rounded-2xl bg-slate-100/90 border border-slate-200 shadow-inner">
          <button
            onClick={() => { setActiveMode('upload'); setCameraActive(false); }}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${
              activeMode === 'upload'
                ? 'bg-teal-600 text-white shadow-md'
                : 'text-slate-600 hover:text-teal-700 hover:bg-white/60'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Image 📷</span>
          </button>

          <button
            onClick={() => { setActiveMode('camera'); setCameraActive(true); }}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${
              activeMode === 'camera'
                ? 'bg-teal-600 text-white shadow-md'
                : 'text-slate-600 hover:text-teal-700 hover:bg-white/60'
            }`}
          >
            <Camera className="w-4 h-4" />
            <span>Take a Photo 📸</span>
          </button>

          <button
            onClick={() => { setActiveMode('manual'); setCameraActive(false); }}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${
              activeMode === 'manual'
                ? 'bg-teal-600 text-white shadow-md'
                : 'text-slate-600 hover:text-teal-700 hover:bg-white/60'
            }`}
          >
            <Keyboard className="w-4 h-4" />
            <span>Enter Food Manually ⌨️</span>
          </button>
        </div>
      </div>

      {/* Main Analyzer Workspace Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Interactive Input Section */}
        <div className="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft">
          
          {/* MODE 1: Upload Image */}
          {activeMode === 'upload' && (
            <div className="space-y-6">
              <div
                onClick={() => fileInputRef.current?.click()}
                className="relative border-2 border-dashed border-teal-200 hover:border-teal-500 rounded-2xl p-8 sm:p-12 text-center bg-teal-50/25 hover:bg-teal-50/60 transition-all cursor-pointer group"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-teal-100/70 text-teal-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <UploadCloud className="w-8 h-8 stroke-[2]" />
                </div>
                <h4 className="font-bold text-slate-800 text-base mb-1">
                  Drag & Drop meal photo here, or <span className="text-teal-600 underline">Browse</span>
                </h4>
                <p className="text-xs text-slate-500">
                  Supports JPG, PNG, WEBP (Max 10MB) • Or choose a quick preset below
                </p>
              </div>

              {/* Quick preset selector for instant testing */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                    Or select a pre-scanned Indian meal:
                  </span>
                  <span className="text-xs font-semibold text-teal-600">Click to preview</span>
                </div>
                <div className="grid grid-cols-3 sm:grid-cols-3 gap-2.5">
                  {PRESET_MEALS.slice(0, 6).map((meal) => {
                    const isSelected = selectedMeal.id === meal.id && !customImage;
                    return (
                      <button
                        key={meal.id}
                        onClick={() => {
                          setSelectedMeal(meal);
                          setCustomImage(null);
                        }}
                        className={`relative p-2 rounded-xl border text-left flex flex-col gap-1.5 transition-all ${
                          isSelected
                            ? 'border-teal-600 bg-teal-50/80 ring-2 ring-teal-500/20 shadow-sm'
                            : 'border-slate-200 hover:border-teal-200 bg-white'
                        }`}
                      >
                        <img
                          src={meal.image}
                          alt={meal.name}
                          className="w-full h-16 rounded-lg object-cover"
                        />
                        <div className="truncate">
                          <p className="font-bold text-slate-800 text-xs truncate">{meal.name}</p>
                          <p className="text-[10px] text-teal-700 font-semibold">{meal.calories} kcal</p>
                        </div>
                        {isSelected && (
                          <div className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full bg-teal-600 text-white flex items-center justify-center text-[10px]">
                            <Check className="w-2.5 h-2.5 stroke-[3]" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* MODE 2: Take a Photo */}
          {activeMode === 'camera' && (
            <div className="space-y-6">
              <div className="relative aspect-video rounded-2xl bg-slate-950 overflow-hidden flex flex-col items-center justify-center border-2 border-teal-500/30">
                {/* Camera Viewfinder graphics */}
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-teal-950/20 via-black to-black opacity-90" />
                
                {/* Simulated Live Viewfinder */}
                <div className="relative z-10 text-center px-4">
                  <div className="w-16 h-16 rounded-full bg-teal-500/20 border border-teal-400 text-teal-300 flex items-center justify-center mx-auto mb-3 animate-pulse">
                    <Camera className="w-8 h-8" />
                  </div>
                  <h4 className="text-white font-bold text-base">Smart Camera Viewfinder</h4>
                  <p className="text-slate-400 text-xs mt-1 max-w-sm mx-auto">
                    Position your dish inside the boundary frame. Ensure adequate lighting for 98% recognition accuracy.
                  </p>

                  {cameraCountdown !== null && (
                    <motion.div
                      initial={{ scale: 0.5, opacity: 0 }}
                      animate={{ scale: 1.2, opacity: 1 }}
                      className="mt-4 text-5xl font-black text-teal-400 font-display"
                    >
                      {cameraCountdown}
                    </motion.div>
                  )}
                </div>

                {/* Viewfinder Corner Guides */}
                <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-teal-400 rounded-tl-lg" />
                <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-teal-400 rounded-tr-lg" />
                <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-teal-400 rounded-bl-lg" />
                <div className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-teal-400 rounded-br-lg" />

                {/* Focus Crosshair */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-20 h-20 border border-teal-400/50 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-teal-400 animate-ping" />
                  </div>
                </div>
              </div>

              {/* Shutter Button */}
              <div className="flex justify-center">
                <motion.button
                  variants={popButtonVariants}
                  initial="initial"
                  whileHover="hover"
                  whileTap="tap"
                  onClick={triggerCameraSnap}
                  disabled={cameraCountdown !== null}
                  className="flex items-center gap-3 px-8 py-3.5 rounded-full bg-teal-600 hover:bg-teal-700 text-white font-bold text-sm shadow-pop cursor-pointer disabled:opacity-50"
                >
                  <div className="w-3.5 h-3.5 rounded-full bg-white animate-pulse" />
                  <span>{cameraCountdown ? 'Capturing...' : 'Capture Meal Photo 📸'}</span>
                </motion.button>
              </div>
            </div>
          )}

          {/* MODE 3: Enter Food Manually */}
          {activeMode === 'manual' && (
            <div className="space-y-5">
              {/* Search Bar */}
              <div className="relative">
                <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search Indian or global dish (e.g. Paneer Rice, Dosa, Dal, Biryani)..."
                  className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white text-sm font-medium transition-all"
                />
              </div>

              {/* Meal Cards List */}
              <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
                {filteredMeals.map((meal) => {
                  const isSelected = selectedMeal.id === meal.id;
                  return (
                    <div
                      key={meal.id}
                      onClick={() => {
                        setSelectedMeal(meal);
                        setCustomImage(null);
                      }}
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-4 ${
                        isSelected
                          ? 'border-teal-600 bg-teal-50/70 shadow-sm'
                          : 'border-slate-100 hover:border-teal-200 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <img
                          src={meal.image}
                          alt={meal.name}
                          className="w-14 h-14 rounded-xl object-cover"
                        />
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700">
                            {meal.category}
                          </span>
                          <h4 className="font-bold text-slate-900 text-sm">{meal.name}</h4>
                          <p className="text-xs text-slate-500">
                            {meal.protein}g Protein • {meal.carbs}g Carbs • {meal.fats}g Fats
                          </p>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="font-black text-slate-800 text-sm">{meal.calories} kcal</span>
                        {isSelected && (
                          <div className="flex items-center gap-1 text-teal-700 text-xs font-bold justify-end mt-1">
                            <Check className="w-3.5 h-3.5" />
                            <span>Selected</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

        </div>

        {/* Right Preview & Action Column (Flow: Preview Image -> Analyze Button) */}
        <div className="lg:col-span-5 bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider">Preview Window</span>
              <h3 className="text-lg font-black text-slate-900">
                {customImage ? 'Uploaded Meal Photo' : selectedMeal.name}
              </h3>
            </div>
            <div className="px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 text-xs font-bold border border-teal-200">
              Ready to Scan
            </div>
          </div>

          {/* Interactive Image Preview with AI Scanning Beam */}
          <div className="relative aspect-[4/3] rounded-2xl overflow-hidden border border-teal-200/80 shadow-md bg-slate-900 group">
            <img
              src={customImage || selectedMeal.image}
              alt="Meal preview"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />

            {/* Laser Scanning Line (Agent 1: Motion animation) */}
            {isScanning && (
              <motion.div
                variants={scannerBeamVariants}
                animate="animate"
                className="absolute left-0 right-0 h-1.5 bg-gradient-to-r from-transparent via-teal-400 to-transparent shadow-[0_0_20px_#14b8a6] pointer-events-none z-20"
              />
            )}

            {/* AI Ingredient Bounding Boxes during scan */}
            {isScanning && (
              <div className="absolute inset-0 bg-teal-950/30 backdrop-blur-[1px] flex flex-col items-center justify-center p-4 text-center z-10">
                <div className="w-12 h-12 rounded-2xl bg-teal-500/20 border-2 border-teal-400 text-teal-300 flex items-center justify-center mb-3 animate-spin">
                  <RefreshCw className="w-6 h-6" />
                </div>
                <p className="text-white font-bold text-sm tracking-wide">AI Neural Vision Active</p>
                <p className="text-teal-200 text-xs mt-1 animate-pulse">{scanStep}</p>
              </div>
            )}

            {/* Static Badge on Preview */}
            {!isScanning && (
              <div className="absolute top-3 right-3 px-3 py-1 rounded-full bg-slate-900/80 backdrop-blur-md text-white text-xs font-semibold border border-white/20 flex items-center gap-1.5">
                <Scan className="w-3 h-3 text-teal-400" />
                <span>Ready</span>
              </div>
            )}
          </div>

          {/* Portion Info */}
          <div className="p-3.5 rounded-2xl bg-teal-50/60 border border-teal-100 flex items-center gap-3 text-xs text-teal-900">
            <Info className="w-4 h-4 text-teal-600 shrink-0" />
            <p>
              AI computes portion depth, volume, and macro splits with sub-5% calorie deviation.
            </p>
          </div>

          {/* THE BIG ANALYZE BUTTON (with 3D Pop Effect) */}
          <motion.button
            variants={popButtonVariants}
            initial="initial"
            whileHover="hover"
            whileTap="tap"
            onClick={handleAnalyze}
            disabled={isScanning}
            className="w-full btn-pop flex items-center justify-center gap-3 py-4 rounded-2xl bg-gradient-to-r from-teal-600 via-teal-500 to-teal-700 text-white font-black text-base shadow-pop cursor-pointer disabled:opacity-50"
          >
            {isScanning ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Analyzing Meal...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5 text-teal-200" />
                <span>Analyze Nutritional Value 🚀</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </motion.button>
        </div>

      </div>

    </div>
  );
}
