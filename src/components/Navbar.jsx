import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Camera, BarChart3, Calendar, User, Menu, X, Bot, Salad } from 'lucide-react';
import { popButtonVariants } from '../animations/motionVariants';

export default function Navbar({ activeTab, setActiveTab }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    { id: 'home', label: 'Home', icon: Salad },
    { id: 'analyzer', label: 'Food Analyzer', icon: Camera, badge: 'AI Core' },
    { id: 'results', label: 'Results', icon: BarChart3 },
    { id: 'daily', label: 'Daily Nutrition', icon: Calendar },
    { id: 'profile', label: 'Profile & Targets', icon: User },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-teal-100/80 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo */}
          <div 
            onClick={() => setActiveTab('home')}
            className="flex items-center gap-3 cursor-pointer group select-none"
          >
            <div className="relative flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 text-white shadow-md shadow-teal-600/20 group-hover:scale-105 transition-transform duration-200">
              <Salad className="w-6 h-6 stroke-[2.2]" />
              <div className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-400 border-2 border-white animate-ping" />
              <div className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-white" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-2xl font-black font-display tracking-tight text-slate-900">
                  Nutri<span className="text-teal-600">AI</span>
                </span>
                <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-md bg-teal-100 text-teal-800 border border-teal-200">
                  v2.0
                </span>
              </div>
              <p className="text-[11px] font-medium text-slate-500 tracking-wide hidden sm:block">
                Intelligent Nutrition Agent
              </p>
            </div>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1.5 bg-slate-50/80 p-1.5 rounded-full border border-slate-200/80 shadow-inner">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`relative flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? 'text-white shadow-sm'
                      : 'text-slate-600 hover:text-teal-700 hover:bg-white/80'
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="navPill"
                      className="absolute inset-0 rounded-full bg-teal-600 shadow-md shadow-teal-600/25"
                      transition={{ type: 'spring', bounce: 0.2, duration: 0.5 }}
                    />
                  )}
                  <span className="relative z-10 flex items-center gap-1.5">
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-teal-100' : 'text-slate-400'}`} />
                    {item.label}
                    {item.badge && (
                      <span className={`text-[9px] px-1.5 py-0.2 rounded-full uppercase tracking-wider font-extrabold ${
                        isActive ? 'bg-teal-700 text-teal-200' : 'bg-teal-100 text-teal-700'
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </span>
                </button>
              );
            })}
          </nav>

          {/* Right Action Button & Agent Badge */}
          <div className="hidden lg:flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-teal-50 border border-teal-200/70 text-[11px] font-medium text-teal-800">
              <Bot className="w-3.5 h-3.5 text-teal-600 animate-pulse" />
              <span>Agents Active:</span>
              <span className="font-semibold text-teal-700">1: Motion & 2: Framework</span>
            </div>

            <motion.button
              variants={popButtonVariants}
              initial="initial"
              whileHover="hover"
              whileTap="tap"
              onClick={() => setActiveTab('analyzer')}
              className="relative group flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-teal-600 to-teal-500 text-white font-semibold text-xs tracking-wide shadow-pop cursor-pointer overflow-hidden"
            >
              <Camera className="w-4 h-4 transition-transform group-hover:rotate-12" />
              <span>Analyze Food</span>
              <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none" />
            </motion.button>
          </div>

          {/* Mobile Menu Trigger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 rounded-xl text-slate-600 hover:bg-slate-100"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="md:hidden bg-white border-b border-teal-100 px-4 pt-2 pb-6 space-y-2 shadow-xl"
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setMobileOpen(false);
                }}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold transition-colors ${
                  isActive ? 'bg-teal-600 text-white' : 'text-slate-700 hover:bg-teal-50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                    isActive ? 'bg-teal-700 text-white' : 'bg-teal-100 text-teal-800'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </motion.div>
      )}
    </header>
  );
}
