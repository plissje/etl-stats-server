const COLOR = /\^[0-9]/g

export function stripQuakeColors(name: string): string {
  return (name || '').replace(COLOR, '')
}
