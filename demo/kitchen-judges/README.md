# Profile Kitchen, judges' edition

This is a copy of David's Profile Kitchen (`autoresearch/studio/static/`), with two pages added for judges. The original files are not changed.

```bash
python3 demo/kitchen-judges/serve.py
```

Then open http://localhost:8790/#/judges

- **Build your agent** (`#/judges`, also a banner on the home page): name your researcher and pick a sigil, then answer six grill questions (D1–D6). You get an editable user model: drag the taste-weight sliders, use the Realist/Rigorist/Maverick presets, toggle principles, or add your own. The closest profile and the agent's six decisions for tonight update live. You can download the model as JSON, and it's saved in your browser.
- **Results** (`#/results`): the strong 9-seed subset from `results/e3b/final_report_all.md`.

Both pages run in the browser, with no API calls and no cost. The rest is the original app, using its own server. Profiles you make there go to `data/judges_researchers`, not the team's folder.
