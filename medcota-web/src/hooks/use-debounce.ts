import { useEffect, useState } from "react"

export function useDebounce<T>(valor: T, ms = 300): T {
  const [debounced, setDebounced] = useState(valor)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(valor), ms)
    return () => clearTimeout(t)
  }, [valor, ms])
  return debounced
}
