import { Trophy, Shield, Crosshair, Star, Info, Target, Zap, Users } from 'lucide-react'

export function HowItWorks() {
  return (
    <main className="max-w-7xl mx-auto px-4 py-12">
      {/* Header Section */}
      <div className="mb-16 text-center">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
          How <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-fuchsia-400">it Works</span>
        </h1>
        <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
          The math behind the gathering rankings. We use a unified system to ensure every player, 
          from the fragging soldier to the objective-focused engineer, is rewarded fairly.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* SR Logic Card */}
        <section className="bg-zinc-900/50 border border-zinc-800 p-8 rounded-2xl backdrop-blur relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Trophy size={120} className="text-violet-500" />
          </div>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-violet-500/20 rounded-lg">
              <Star className="text-violet-400" size={24} />
            </div>
            <h2 className="text-2xl font-bold text-white">The Skill Rating (SR)</h2>
          </div>
          <p className="text-zinc-400 mb-6 leading-relaxed">
            Our Skill Rating uses the <strong className="text-zinc-200">OpenSkill (Plackett-Luce)</strong> model. 
            Unlike simple ELO systems, it tracks your skill (μ) and the system's confidence in that skill (σ). 
            Your visible SR is a conservative estimate of your true skill.
          </p>
          <div className="space-y-4">
            <div className="flex items-start gap-3 bg-zinc-950/50 p-4 rounded-xl border border-zinc-800/50">
              <Zap className="text-amber-400 shrink-0 mt-1" size={18} />
              <div>
                <p className="text-sm font-semibold text-zinc-200 uppercase tracking-wider mb-1">The 60/40 Blend</p>
                <p className="text-zinc-400 text-sm">Your SR change after a match is a weighted blend: 60% is based on your <span className="text-fuchsia-400">Personal Performance</span>, and 40% is based on the <span className="text-violet-400">Match Outcome</span> (Winning/Losing).</p>
              </div>
            </div>
          </div>
        </section>

        {/* Unified Efficiency Card */}
        <section className="bg-zinc-900/50 border border-zinc-800 p-8 rounded-2xl backdrop-blur relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Target size={120} className="text-fuchsia-500" />
          </div>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-fuchsia-500/20 rounded-lg">
              <Target className="text-fuchsia-400" size={24} />
            </div>
            <h2 className="text-2xl font-bold text-white">Unified Efficiency (UE)</h2>
          </div>
          <p className="text-zinc-400 mb-6 leading-relaxed">
            Standard K/D is biased against support roles. We use <strong className="text-zinc-200">Unified Efficiency</strong>, 
            which converts every positive contribution into "Contribution Points" to measure your impact.
          </p>
          <div className="bg-zinc-950/80 p-6 rounded-xl border border-zinc-800 font-mono text-sm">
            <div className="flex justify-between items-center mb-2 pb-2 border-b border-zinc-800">
              <span className="text-zinc-500 uppercase tracking-tighter">Contribution Formula</span>
            </div>
            <div className="text-fuchsia-400 text-base py-2">
              UE = (Points / (Points + Deaths + SelfKills)) * 100
            </div>
          </div>
        </section>
      </div>

      {/* Points Table */}
      <section className="mb-16 mt-12">
        <div className="flex items-center gap-3 mb-8">
          <Info className="text-violet-400" size={28} />
          <h2 className="text-3xl font-bold text-white">Contribution Values</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Kill', value: '1.0 pt', icon: <Crosshair className="text-red-400" />, desc: 'Fragging power' },
            { label: 'Revive', value: '1.0 pt', icon: <Star className="text-blue-400" />, desc: 'Parity with kills' },
            { label: 'Ammo Pack', value: '0.25 pt', icon: <Zap className="text-amber-400" />, desc: 'Per pack dropped' },
            { label: 'Objective XP', value: '0.10 pt', icon: <Shield className="text-emerald-400" />, desc: 'Per 1 XP earned' },
          ].map((item, i) => (
            <div key={i} className="p-6 bg-zinc-900/30 border border-zinc-800 rounded-xl hover:border-zinc-700 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-zinc-950 rounded-lg border border-zinc-800">
                  {item.icon}
                </div>
                <span className="text-xl font-bold text-white tracking-tight">{item.value}</span>
              </div>
              <h3 className="font-bold text-zinc-200 mb-1">{item.label}</h3>
              <p className="text-zinc-500 text-sm">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Role Explanations */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="p-8 bg-zinc-900/20 border-l-4 border-violet-500 rounded-lg">
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Users size={20} className="text-violet-400" />
              Why this system?
            </h3>
            <p className="text-zinc-400 leading-relaxed">
              In base Wolfenstein: ET, medics and engineers often have low K/Ds but win the game. By giving a <strong className="text-violet-400">Revive the same weight as a Kill</strong>, and rewarding objective progression via XP, we ensure the standings reflect the players who actually carry their teams to victory.
            </p>
          </div>
          <div className="p-8 bg-zinc-900/20 border-l-4 border-fuchsia-500 rounded-lg">
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Star size={20} className="text-fuchsia-400" />
              How are MVPs selected?
            </h3>
            <p className="text-zinc-400 leading-relaxed">
              The Most Valuable Player (MVP) is awarded automatically to the player with the highest <strong className="text-fuchsia-400">Performance Score</strong> in a match. This score is heavily weighted toward the winning team, but an exceptional performance on the losing side can still earn the medal.
            </p>
          </div>
        </div>
        
        {/* Quick Tips */}
        <aside className="p-8 bg-gradient-to-b from-zinc-900 to-zinc-950 border border-zinc-800 rounded-2xl">
          <h3 className="text-lg font-bold text-white mb-6 uppercase tracking-widest text-zinc-500">Quick Tips</h3>
          <ul className="space-y-6">
            <li className="flex gap-4">
              <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-2 shrink-0" />
              <p className="text-sm text-zinc-300">New players start at <span className="font-bold text-white">1500 SR</span>. Your first matches will cause larger SR changes.</p>
            </li>
            <li className="flex gap-4">
              <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-2 shrink-0" />
              <p className="text-sm text-zinc-300">Win as a team for the <span className="font-bold text-white">40% Team Bonus</span>. It is almost always better to win the game than to hunt for extra kills.</p>
            </li>
            <li className="flex gap-4">
              <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-2 shrink-0" />
              <p className="text-sm text-zinc-300">Engineers can maintain a high SR just by doing <span className="font-bold text-white">Objective work</span>, thanks to the XP contribution logic.</p>
            </li>
          </ul>
        </aside>
      </section>
    </main>
  )
}
