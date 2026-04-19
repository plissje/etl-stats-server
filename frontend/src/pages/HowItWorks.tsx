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
                <p className="text-sm font-semibold text-zinc-200 uppercase tracking-wider mb-1">The 75/25 Hybrid Model</p>
                <p className="text-zinc-400 text-sm">Your SR change is calculated using a <span className="text-fuchsia-400">75% Performance</span> signal and a <span className="text-violet-400">25% Team Outcome</span> signal. This ensures that losing a random gather doesn't tank your rating if you played exceptionally well.</p>
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
            <div className="text-fuchsia-400 text-base py-2 font-bold tracking-tight">
              UE = (Points / (Points + (Deaths * 1.25) + (SelfKills * 0.5))) * 100
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
            { label: 'Kill', value: '1.20 pt', icon: <Crosshair className="text-red-400" />, desc: 'Primary combat reward' },
            { label: 'Revive', value: '0.20 pt', icon: <Star className="text-blue-400" />, desc: 'Team support impact' },
            { label: 'Death', value: '-1.25x', icon: <Zap className="text-amber-400" />, desc: 'Denominator penalty' },
            { label: 'Objective XP', value: '0.30 pt', icon: <Shield className="text-emerald-400" />, desc: 'Plants & Engineering' },
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
              In Wolfenstein: ET, support roles are often undervalued. Our system is <strong className="text-violet-400">Class-Aware</strong>: Medics have XP weights capped at <strong className="text-violet-400">0.05</strong> to prioritize revives, while objective classes (Engineers/Soldiers/Coverts) receive a <strong className="text-violet-400">0.30 XP weight</strong> to reward mission-critical plays.
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
          <div className="bg-zinc-900/40 border border-fuchsia-500/20 p-8 rounded-2xl">
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Zap size={20} className="text-amber-400" />
              Stopwatch Logic
            </h3>
            <p className="text-zinc-400 leading-relaxed mb-6">
              Competitive ET is played in two rounds. The winner is determined by the <strong className="text-white">fastest objective completion</strong>. 
              If Team A finishes in 12:30, Team B must beat that time to win. If neither team completes the objective, the match is a <span className="text-zinc-300 font-bold italic">Draw</span>.
            </p>
            <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
              <p className="text-xs text-amber-200 uppercase tracking-widest font-bold mb-1">Set Time Winner</p>
              <p className="text-sm text-amber-100/80">
                The UI highlights the <span className="font-bold text-emerald-400 underline decoration-emerald-500/30">emerald green time</span> as the winning set time.
              </p>
            </div>
          </div>
          <div className="bg-zinc-900/40 border border-fuchsia-500/20 p-8 rounded-2xl">
            <h3 className="text-xl font-bold text-white mb-4">The 75/25 Competitive Rule</h3>
            <p className="text-zinc-400 leading-relaxed mb-6">
              In scramble-based gathers, "Team Win" can sometimes be lucky. To fix this, we split each match:
              <strong className="text-fuchsia-400"> 75%</strong> individual performance vs team avg, and 
              <strong className="text-fuchsia-400"> 25%</strong> overall team result.
            </p>
            <div className="p-4 bg-fuchsia-500/10 border border-fuchsia-500/30 rounded-xl">
              <p className="text-xs text-fuchsia-200 uppercase tracking-widest font-bold mb-1">Sliding Confidence Scale</p>
              <p className="text-sm text-fuchsia-100/80">
                A <span className="font-bold text-white italic">1.15x Impact</span> multiplier is applied to your performance. 
                We use <span className="text-white italic">2.0σ</span> for your first 10 games to find your rank fast, then slide to <span className="text-white italic">3.0σ</span> for maximum stability as a veteran.
              </p>
            </div>
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
              <p className="text-sm text-zinc-300">Win as a team for the <span className="font-bold text-white">25% Team Result</span>. It is still better to win the game, but your personal impact is the primary driver of your rank.</p>
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
