# Profile Kitchen, judges' edition

This is a copy of David's Profile Kitchen (`autoresearch/studio/static/`), with two pages added for judges. The original files are not changed.

```bash
python3 demo/kitchen-judges/serve.py
```

Then open http://localhost:8790/#/judges

- **Build your agent** (`#/judges`): six questions modelled on the grill.py decision points D1–D6. Your answers become a user model, shown as taste weights and principles, and the page shows which eval-rewrite design your agent would pick and how that profile measured on Kimi K2.6.
- **Results** (`#/results`): the strong 9-seed subset from `results/e3b/final_report_all.md`.

Both pages run in the browser, with no API calls and no cost. The rest is the original app, using its own server. Profiles you make there go to `data/judges_researchers`, not the team's folder.
