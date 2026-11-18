# Stayline defence deck

From `slides/`, run `npm run dev` and open `http://localhost:3030`. Presenter view is at `/presenter`.

`npm run data` rebuilds `generated/deck.json` from committed evaluation files. `npm run notes` rebuilds `slides.md` from `docs/defence/script.md`. Both run automatically before development, build, and export.

Run `npm run build` to check the deck. Run `npm run export` to write a PDF. Add optional live demo screenshots at `public/media/demo-1.png` through `demo-4.png`.
