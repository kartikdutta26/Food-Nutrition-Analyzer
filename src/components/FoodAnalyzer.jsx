import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertCircle,
  Camera,
  Check,
  Image as ImageIcon,
  Info,
  Keyboard,
  RefreshCw,
  Search,
  Sparkles,
  UploadCloud,
} from 'lucide-react';
import { popButtonVariants } from '../animations/motionVariants';
import {
  buildFoodLookupRequest,
  formatFoodLookupError,
  getFoodMatchChoices,
  submitFoodNameLookup,
} from '../utils/foodLookup';

const SUPPORTED_SAMPLE_FOODS = [
  'Paneer Rice Bowl',
  'Crispy Masala Dosa with Sambar',
  'Yellow Dal Tadka & Brown Rice',
  'Grilled Chicken Tikka Quinoa Bowl',
  'Palak Paneer with Multigrain Roti',
  'Tropical Fruit & Greek Yogurt Platter',
];

export default function FoodAnalyzer({ onAnalysisComplete, onAnalyzeFood }) {
  const [activeMode, setActiveMode] = useState('manual');
  const [foodName, setFoodName] = useState('');
  const [customImage, setCustomImage] = useState('');
  const [fileName, setFileName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [pendingSelection, setPendingSelection] = useState(null);
  const fileInputRef = useRef(null);
  const requestVersionRef = useRef(0);
  const requestControllerRef = useRef(null);

  const cancelLookup = () => {
    requestVersionRef.current += 1;
    requestControllerRef.current?.abort();
    requestControllerRef.current = null;
    setPendingSelection(null);
    setIsLoading(false);
  };

  useEffect(() => () => {
    requestVersionRef.current += 1;
    requestControllerRef.current?.abort();
  }, []);

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Choose an image file (JPG, PNG, or WEBP).');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('The image must be 10 MB or smaller.');
      return;
    }

    setError('');
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (loadEvent) => setCustomImage(loadEvent.target?.result || '');
    reader.onerror = () => setError('The selected image could not be previewed.');
    reader.readAsDataURL(file);
    event.target.value = '';
  };

  const runLookup = async (lookup, errorFoodName, { showMatches = false } = {}) => {
    setError('');
    setIsLoading(true);
    requestControllerRef.current?.abort();
    const controller = new AbortController();
    const requestVersion = requestVersionRef.current + 1;
    requestVersionRef.current = requestVersion;
    requestControllerRef.current = controller;
    try {
      const options = { signal: controller.signal };
      const result = lookup.fdc_id == null
        ? await submitFoodNameLookup(lookup.food_name, onAnalyzeFood, options)
        : await onAnalyzeFood(lookup, options);
      if (requestVersion !== requestVersionRef.current) return;
      const matches = getFoodMatchChoices(result);
      if (showMatches && matches.length > 1) {
        setPendingSelection({ result, matches });
      } else {
        setPendingSelection(null);
        onAnalysisComplete(result);
      }
    } catch (requestError) {
      if (requestVersion !== requestVersionRef.current || requestError?.name === 'AbortError') return;
      setError(formatFoodLookupError(requestError, errorFoodName));
    } finally {
      if (requestVersion === requestVersionRef.current) {
        requestControllerRef.current = null;
        setIsLoading(false);
      }
    }
  };

  const handleAnalyze = async (event) => {
    event.preventDefault();
    const lookup = buildFoodLookupRequest(foodName);
    if (!lookup) {
      setError('Enter a food name to look up in USDA FoodData Central.');
      return;
    }

    const normalizedName = lookup.food_name;
    setPendingSelection(null);
    await runLookup(lookup, normalizedName, { showMatches: true });
  };

  const handleSelectMatch = async (match) => {
    if (!pendingSelection || isLoading) return;
    const selectedId = Number(match.fdc_id);
    if (selectedId === Number(pendingSelection.result.fdc_id)) {
      setPendingSelection(null);
      onAnalysisComplete(pendingSelection.result);
      return;
    }

    const normalizedName = foodName.trim();
    await runLookup(
      { food_name: normalizedName, fdc_id: selectedId },
      normalizedName,
    );
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold uppercase tracking-wider mb-3">
          <Sparkles className="w-3.5 h-3.5 text-teal-600" />
          <span>USDA FoodData Central Lookup</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-black font-display text-slate-900 tracking-tight">
          Analyze Your Meal
        </h2>
        <p className="text-slate-600 mt-2 text-base">
          Look up a food name in USDA FoodData Central. The sample preset buttons remain available as clearly labeled demo data.
        </p>
      </div>

      <div className="flex justify-center mb-8">
        <div className="inline-flex p-1.5 rounded-2xl bg-slate-100/90 border border-slate-200 shadow-inner">
          {[
            { id: 'upload', label: 'Upload Image 📷', Icon: UploadCloud },
            { id: 'camera', label: 'Take a Photo 📸', Icon: Camera },
            { id: 'manual', label: 'Enter Food Manually ⌨️', Icon: Keyboard },
          ].map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => { cancelLookup(); setActiveMode(id); setError(''); }}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 ${activeMode === id ? 'bg-teal-600 text-white shadow-md' : 'text-slate-600 hover:text-teal-700 hover:bg-white/60'}`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <div className="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft">
          {activeMode === 'upload' && (
            <div className="space-y-5">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full relative border-2 border-dashed border-teal-200 hover:border-teal-500 rounded-2xl p-8 sm:p-12 text-center bg-teal-50/25 hover:bg-teal-50/60 transition-all cursor-pointer group"
              >
                <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-teal-100/70 text-teal-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <UploadCloud className="w-8 h-8 stroke-[2]" />
                </div>
                <h4 className="font-bold text-slate-800 text-base mb-1">
                  {fileName || 'Choose a meal photo'}
                </h4>
                <p className="text-xs text-slate-500">JPG, PNG, or WEBP • Maximum 10 MB • Preview stays in this browser</p>
              </button>
              <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200/80 flex items-start gap-3">
                <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <p className="text-sm text-amber-950">Image recognition is not implemented. This photo is only previewed locally and is never sent to the backend.</p>
              </div>
            </div>
          )}

          {activeMode === 'camera' && (
            <div className="relative aspect-video rounded-2xl bg-slate-950 overflow-hidden flex flex-col items-center justify-center border-2 border-teal-500/30 p-6 text-center">
              <div className="w-16 h-16 rounded-full bg-teal-500/20 border border-teal-400 text-teal-300 flex items-center justify-center mb-3">
                <Camera className="w-8 h-8" />
              </div>
              <h4 className="text-white font-bold text-base">Camera analysis unavailable</h4>
              <p className="text-slate-300 text-xs mt-2 max-w-sm">Image recognition is unavailable. Use the food name lookup to retrieve USDA nutrition data or a labeled sample preset.</p>
            </div>
          )}

          {activeMode === 'manual' && (
            <form id="food-name-lookup-form" onSubmit={handleAnalyze} className="space-y-5">
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="relative min-w-0 flex-1">
                  <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={foodName}
                    onChange={(event) => {
                      cancelLookup();
                      setFoodName(event.target.value);
                      setError('');
                    }}
                    placeholder="Enter a food name"
                    maxLength={120}
                    className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-slate-50 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white text-sm font-medium transition-all"
                    aria-label="Food name"
                  />
                </div>
                <motion.button
                  variants={popButtonVariants}
                  initial="initial"
                  whileHover="hover"
                  whileTap="tap"
                  type="submit"
                  disabled={isLoading || !foodName.trim()}
                  className="inline-flex min-h-[52px] w-full shrink-0 items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-teal-600 via-teal-500 to-teal-700 px-5 text-sm font-black text-white shadow-pop transition-opacity sm:w-auto disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isLoading
                    ? <><RefreshCw className="h-4 w-4 animate-spin" /><span>Searching…</span></>
                    : <><Search className="h-4 w-4" /><span>Search</span></>}
                </motion.button>
              </div>
              <div className="rounded-2xl border border-teal-100 bg-teal-50/40 p-4">
                <p className="text-xs font-bold uppercase tracking-wider text-teal-800 mb-2">Sample preset foods</p>
                <div className="flex flex-wrap gap-2">
                  {SUPPORTED_SAMPLE_FOODS.map((name) => (
                    <button
                      type="button"
                      key={name}
                      onClick={() => { cancelLookup(); setFoodName(name); setError(''); }}
                      className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${foodName === name ? 'border-teal-600 bg-teal-600 text-white' : 'border-teal-200 bg-white text-teal-800 hover:bg-teal-50'}`}
                    >
                      {foodName === name && <Check className="inline w-3 h-3 mr-1" />}{name}
                    </button>
                  ))}
                </div>
              </div>
              <p className="text-xs text-slate-500">Only the food name is sent to the backend. USDA data is retrieved for matches; unsupported foods return no match.</p>
            </form>
          )}

          {pendingSelection && (
            <section aria-label="Matching USDA foods" className="mt-5 rounded-2xl border border-teal-100 bg-teal-50/40 p-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-teal-800">Choose a USDA food match</h3>
              <p className="mt-1 mb-3 text-xs text-slate-600">Select the food entry that best matches what you ate. Nutrition and serving details load for your selection.</p>
              <div className="space-y-2">
                {pendingSelection.matches.map((match) => (
                  <button
                    type="button"
                    key={match.fdc_id}
                    onClick={() => handleSelectMatch(match)}
                    disabled={isLoading}
                    className="flex w-full items-center justify-between gap-3 rounded-xl border border-teal-200 bg-white px-3 py-2.5 text-left transition-colors hover:border-teal-500 hover:bg-teal-50 disabled:cursor-wait disabled:opacity-60"
                  >
                    <span>
                      <span className="block text-sm font-semibold text-slate-800">{match.name}</span>
                      <span className="mt-0.5 block text-[11px] text-slate-500">{match.category || 'USDA FoodData Central'}</span>
                    </span>
                    <span className="shrink-0 text-xs font-bold text-teal-700">Select</span>
                  </button>
                ))}
              </div>
              {isLoading && <p role="status" className="mt-3 text-xs font-semibold text-teal-800">Loading nutrition for the selected food…</p>}
            </section>
          )}

          {error && (
            <div role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 flex gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="lg:col-span-5 bg-white rounded-3xl p-6 sm:p-8 border border-teal-100 shadow-card-soft space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider">Preview Window</span>
              <h3 className="text-lg font-black text-slate-900">{activeMode === 'manual' ? (foodName.trim() || 'Food name') : fileName || 'No image selected'}</h3>
            </div>
            <div className="px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 text-xs font-bold border border-teal-200">{activeMode === 'manual' ? 'Name lookup' : 'Local only'}</div>
          </div>

          <div className="relative aspect-[4/3] rounded-2xl overflow-hidden border border-teal-200/80 shadow-md bg-slate-900 flex items-center justify-center">
            {customImage && activeMode === 'upload' ? (
              <img src={customImage} alt="Local food photo preview" className="w-full h-full object-cover" />
            ) : (
              <div className="text-center text-slate-300 p-6">
                <ImageIcon className="w-12 h-12 mx-auto mb-3 text-teal-300" />
                <p className="text-sm font-semibold">No food image is analyzed</p>
                <p className="text-xs text-slate-400 mt-1">Nutrition comes from a USDA lookup or a labeled sample preset.</p>
              </div>
            )}
          </div>

          <div className="p-3.5 rounded-2xl bg-teal-50/60 border border-teal-100 flex items-start gap-3 text-xs text-teal-900">
            <Info className="w-4 h-4 text-teal-600 shrink-0" />
            <p>Uploaded photos are only previewed locally. Nutrition lookup uses the food name; sample preset values are labeled as demonstration data.</p>
          </div>

          {activeMode !== 'manual' && (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-center text-xs font-semibold text-slate-600">
              {activeMode === 'camera' ? 'Camera analysis is unavailable' : 'Image analysis is unavailable'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
