# Stayline defence deck

Slidev deck for the defence: ten beats, dark full-bleed, in the style of the Clausier deck.

From `slides/`, run `npm run dev` and open `http://localhost:3030`. Presenter view is at `/presenter`.

- `npm run data` rebuilds `generated/deck.json` from committed evaluation files. Every figure on a slide comes from it.
- `npm run notes` rebuilds `slides.md` from `docs/defence/script.md` (speaker notes are the script word for word).
- `npm run build` checks the deck. `npm run export` writes a PDF backup (final state of each slide).

## How it moves

- `world/engine.ts` is one canvas of 1,500 glowing particles. `world/formations.ts` says where they go on each slide and each click (the seized contract and its five restrictions, the 90 evaluation runs as dots, the before and after, the two models). On every change the particles flow there with a staggered, curved tween.
- `components/Headline.vue` reveals each title word by word (GSAP SplitText) and draws the underline.
- Slides reveal their parts on each click (`useBeat`), numbers count up (`useCount`), and the failed trace draws itself.
- `global-top.vue` is the footer: speaker, page, progress.

Demo screenshots are `public/media/demo-1.png` through `demo-4.png`.
