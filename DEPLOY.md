# Деплой на GitHub Pages — SIMILIS demo

Репозиторий: **`similis-demo`** · public. Право на публикацию данных ИИМК РАН/НовГУ подтверждено.

```bash
cd "/Users/revvoensvet/Documents/IR/110-test_tasks/similis/prototype"

grep -qxF "110-test_tasks/similis/prototype/" "/Users/revvoensvet/Documents/IR/.gitignore" \
  || echo "110-test_tasks/similis/prototype/" >> "/Users/revvoensvet/Documents/IR/.gitignore"

npm install
gh auth setup-git
git init -b main && git add . && git commit -m "SIMILIS.AI demo — real artifacts, offline similarity proxy, RU/EN"
gh repo create similis-demo --public --source=. --remote=origin --push
npm run deploy
gh api --method POST repos/{owner}/{repo}/pages -f "source[branch]=gh-pages" -f "source[path]=/" \
  || echo "Pages вручную: Settings → Pages → gh-pages /(root)"
```

URL: `https://<username>.github.io/similis-demo/` (после `Published` подожди 1–2 мин, открой с `?v=1` для обхода кэша).

Обновить: `git add . && git commit -m "update" && git push && npm run deploy`.

Реальные эмбеддинги (опц., на маке): `pip install torch torchvision open_clip_torch && python3 verify/embed_real.py` → `npm run deploy`.
