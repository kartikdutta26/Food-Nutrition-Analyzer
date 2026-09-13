import React from 'react';
import { Salad, Heart, Shield, Sparkles } from 'lucide-react';

export default function Footer({ setActiveTab }) {
  return (
    <footer className="bg-white border-t border-teal-100/80 pt-12 pb-8 mt-16 text-slate-600">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          
          <div className="space-y-3 md:col-span-1">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-teal-600 text-white flex items-center justify-center">
                <Salad className="w-4 h-4" />
              </div>
              <span className="font-black font-display text-xl text-slate-900">
                Nutri<span className="text-teal-600">AI</span>
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Your food. Your goals. One intelligent nutrition agent. Designed with high-accuracy computer vision for Indian & global cuisines.
            </p>
          </div>

          <div>
            <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider mb-3">
              Application Flows
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <button onClick={() => setActiveTab('home')} className="hover:text-teal-600 transition-colors">
                  🏠 Home Landing Page
                </button>
              </li>
              <li>
                <button onClick={() => setActiveTab('analyzer')} className="hover:text-teal-600 transition-colors">
                  📸 AI Food Analyzer
                </button>
              </li>
              <li>
                <button onClick={() => setActiveTab('results')} className="hover:text-teal-600 transition-colors">
                  📊 Results & Nutrient Score
                </button>
              </li>
              <li>
                <button onClick={() => setActiveTab('daily')} className="hover:text-teal-600 transition-colors">
                  📅 Daily Nutrition Tracker
                </button>
              </li>
              <li>
                <button onClick={() => setActiveTab('profile')} className="hover:text-teal-600 transition-colors">
                  👤 Profile & Target Goals
                </button>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider mb-3">
              Smart Features
            </h4>
            <ul className="space-y-2 text-xs text-slate-500">
              <li>• Indian Food Intelligence (4,500+ dishes)</li>
              <li>• Real-time Glycemic Indexing</li>
              <li>• Portion Scale Estimation</li>
              <li>• Automated Micronutrient Breakdown</li>
            </ul>
          </div>

          <div>
            <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider mb-3">
              Multi-Agent Architecture
            </h4>
            <div className="p-3.5 rounded-2xl bg-teal-50 border border-teal-200 text-xs text-teal-900 space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                <span>Agent 1: Motion & Micro-physics</span>
              </p>
              <p className="font-bold flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-teal-600" />
                <span>Agent 2: Framework & Teal Theme</span>
              </p>
            </div>
          </div>

        </div>

        <div className="border-t border-slate-100 pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-4">
          <p>© 2026 NutriAI Platform. Crafted for healthy living.</p>
          <div className="flex items-center gap-1">
            <span>Powered by intelligent nutrition models</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
