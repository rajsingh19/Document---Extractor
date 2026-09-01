import React from 'react';
import { Files, Zap, Flame, Droplets, Recycle, ShieldCheck } from 'lucide-react';

export default function StatsCards({ stats }) {
  const cards = [
    {
      title: 'Processed Documents',
      value: stats ? stats.total_documents : 0,
      subtext: `${stats ? stats.processed_count : 0} validated, ${stats ? stats.failed_count : 0} failed`,
      icon: Files,
      color: 'from-blue-500/20 to-indigo-500/10',
      textColor: 'text-blue-400',
      borderColor: 'border-blue-500/30'
    },
    {
      title: 'Extracted Energy',
      value: stats && stats.total_energy_kwh > 0 ? `${(stats.total_energy_kwh / 1000).toFixed(1)}k kWh` : '0 kWh',
      subtext: 'Active consumption recorded',
      icon: Zap,
      color: 'from-amber-500/20 to-yellow-500/10',
      textColor: 'text-amber-400',
      borderColor: 'border-amber-500/30'
    },
    {
      title: 'Total Carbon (GHG)',
      value: stats && stats.total_emissions_tco2e > 0 ? `${stats.total_emissions_tco2e.toFixed(1)} tCO2e` : '0 tCO2e',
      subtext: 'Scope 1 & Scope 2 Emissions',
      icon: Flame,
      color: 'from-emerald-500/20 to-teal-500/10',
      textColor: 'text-emerald-400',
      borderColor: 'border-emerald-500/30'
    },
    {
      title: 'Water & Waste Metrics',
      value: stats && (stats.total_water_kl > 0 || stats.total_waste_kg > 0)
        ? `${stats.total_water_kl.toFixed(0)} kL / ${(stats.total_waste_kg / 1000).toFixed(1)} MT`
        : '0 kL / 0 MT',
      subtext: 'Water usage & circular waste',
      icon: Droplets,
      color: 'from-cyan-500/20 to-sky-500/10',
      textColor: 'text-cyan-400',
      borderColor: 'border-cyan-500/30'
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`glass-card p-5 rounded-2xl border ${card.borderColor} bg-gradient-to-br ${card.color} relative overflow-hidden transition-all hover:scale-[1.01] hover:shadow-lg`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  {card.title}
                </p>
                <h3 className="text-2xl font-bold text-white mt-1.5 tracking-tight">
                  {card.value}
                </h3>
                <p className="text-xs text-slate-400 mt-1 font-medium">
                  {card.subtext}
                </p>
              </div>
              <div className={`p-3 rounded-xl bg-slate-900/60 border border-slate-700/60 ${card.textColor}`}>
                <Icon className="w-6 h-6" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
