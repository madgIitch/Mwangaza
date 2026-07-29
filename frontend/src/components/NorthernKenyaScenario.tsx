import { useState } from "react";

const units = [
  { id: "KEN-023", name: "Turkana", severity: "critical", score: 0.84, ndvi: -0.42, rainfall: -0.48 },
  { id: "KEN-010", name: "Marsabit", severity: "warning", score: 0.68, ndvi: -0.31, rainfall: -0.35 },
  { id: "KEN-011", name: "Isiolo", severity: "watch", score: 0.51, ndvi: -0.2, rainfall: -0.24 }
] as const;

const messages = {
  en: (unit: string) => `Review water access in ${unit}.`,
  sw: (unit: string) => `Kagua upatikanaji wa maji katika ${unit}.`,
  so: (unit: string) => `Hubi helitaanka biyaha ee ${unit}.`
};

export function NorthernKenyaScenario(): JSX.Element {
  const [selectedId, setSelectedId] = useState("KEN-023");
  const [language, setLanguage] = useState<keyof typeof messages>("en");
  const selected = units.find((unit) => unit.id === selectedId) ?? units[0];
  return (
    <section className="kenya-scenario" aria-label="Northern Kenya demo scenario">
      <div className="section-heading"><div><p className="eyebrow">Offline demo · northern-kenya-2026-03-demo-v1</p><h2>Northern Kenya subnational scenario</h2></div><span className="severity-badge" data-severity={selected.severity}>{selected.severity}</span></div>
      <div className="kenya-scenario-grid">
        <div><h3>Accessible district selection</h3>{units.map((unit) => <button type="button" key={unit.id} data-selected={unit.id === selected.id} onClick={() => setSelectedId(unit.id)}>{unit.name}<small>{unit.id} · {unit.severity}</small></button>)}</div>
        <div aria-live="polite"><h3>{selected.name} · {selected.id}</h3><p><strong>Composite score:</strong> {selected.score}</p><p>NDVI anomaly {selected.ndvi} · Rainfall anomaly {selected.rainfall}</p><p><strong>Operational area:</strong> {selected.id}</p></div>
        <div><label>Notification language <select aria-label="Notification language" value={language} onChange={(event) => setLanguage(event.target.value as keyof typeof messages)}><option value="en">English</option><option value="sw">Kiswahili</option><option value="so">Somali</option></select></label><p><strong>Simulated notification</strong></p><p>{messages[language](selected.name)}</p><small>Requested/effective language: {language}/{language}</small></div>
      </div>
    </section>
  );
}
