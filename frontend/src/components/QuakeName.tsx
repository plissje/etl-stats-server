
const QUAKE_COLORS: Record<string, string> = {
  // Standard Q3/ET (Mapped 0 to a visible Silver/Gray for dark mode)
  '0': '#A0A0A0', '1': '#FF4136', '2': '#2ECC40', '3': '#FFDC00', 
  '4': '#0074D9', '5': '#7FDBFF', '6': '#F012BE', '7': '#FFFFFF', 
  '8': '#FF851B', '9': '#AAAAAA',
  
  // Extended ET colors (approximate mapping)
  'a': '#FF851B', 'b': '#2ECC40', 'c': '#F012BE', 'd': '#0074D9', 
  'e': '#B10DC9', 'f': '#7FDBFF', 'g': '#CDFFCC', 'h': '#008000', 
  'i': '#800000', 'j': '#800000', 'k': '#804000', 'l': '#FFB347', 
  'm': '#008080', 'n': '#8080C0', 'o': '#C08040', 'p': '#A0A0A0', 
  'q': '#A0A0A0', 'r': '#808000', 's': '#808000', 't': '#A0A0A0',
  'u': '#A0A0A0', 'v': '#A0A0A0', 'w': '#A0A0A0', 'x': '#A0A0A0', 
  'y': '#A0A0A0', 'z': '#A0A0A0',
  '*': '#FFFFFF', '?': '#FFFFFF'
}

export function QuakeName({ name }: { name?: string | null }) {
  if (!name) return <span>-</span>
  
  // Split around any ^ followed by exactly one character
  const parts = name.split(/(\^.)/g)
  let currentColor = QUAKE_COLORS['7']
  
  const spans = []
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i]
    if (part.startsWith('^') && part.length === 2) {
      const code = part[1].toLowerCase()
      if (QUAKE_COLORS[code]) {
        currentColor = QUAKE_COLORS[code]
      }
    } else if (part.length > 0) {
      spans.push(<span key={i} style={{ color: currentColor }}>{part}</span>)
    }
  }

  return <span className="font-bold drop-shadow-md text-shadow-sm tracking-wide">{spans}</span>
}
