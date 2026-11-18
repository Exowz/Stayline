import '@fontsource/instrument-serif/400.css'
import '@fontsource/instrument-serif/400-italic.css'
import '@fontsource-variable/onest/wght.css'
import '@fontsource-variable/jetbrains-mono/wght.css'
import '../style.css'
import { defineAppSetup } from '@slidev/types'
import gsap from 'gsap'

gsap.ticker.lagSmoothing(0)

export default defineAppSetup(() => {})
