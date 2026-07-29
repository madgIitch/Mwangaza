import type { LandingLinks } from "../config/landing";
import { landingLinks, validPublicUrl } from "../config/landing";

export function LandingPage({ links = landingLinks }: { links?: LandingLinks }): JSX.Element {
  const ctas = [
    { key: "dashboard", label: "Open dashboard", href: links.dashboard, primary: true },
    { key: "demo", label: "Explore the demo", href: links.demo, primary: false },
    { key: "github", label: "View on GitHub", href: links.github, primary: false }
  ].filter(item => validPublicUrl(item.href));
  return <main className="landing-page">
    <header className="landing-nav"><a className="landing-wordmark" href="/landing">Mwangaza</a><nav aria-label="Landing navigation"><a href="#approach">How it works</a><a href="/overview?layer=episodes">Persistent episodes</a><a href="/about">About</a></nav></header>
    <section className="landing-hero">
      <img src="/landing/hero-northern-kenya.png" alt="Aerial view of a braided dry riverbed across semi-arid Northern Kenya at dawn" />
      <div className="landing-hero-shade" />
      <div className="landing-hero-copy">
        <p className="landing-kicker">Satellite evidence for anticipatory action</p>
        <h1 aria-label="Mwangaza - Bringing Light to Early Action"><span>Mwangaza</span>Bringing Light to Early Action</h1>
        <p>See where drought conditions are active, how long they have persisted, and whether they may continue over the next 30 to 180 days.</p>
        <div className="landing-actions">{ctas.map(cta => <a className={cta.primary ? "primary" : "secondary"} href={cta.href} key={cta.key}>{cta.label}</a>)}</div>
      </div>
      <a className="landing-scroll" href="#problem">Scroll to understand <span aria-hidden="true">↓</span></a>
    </section>

    <section className="landing-problem" id="problem"><p className="landing-section-label">The problem</p><h2>Drought signals arrive before decisions do.</h2><p>Satellite and climate observations are abundant, but local teams still need a clear, traceable view of where conditions are worsening and what should be reviewed next.</p></section>

    <section className="landing-approach" id="approach"><div><p className="landing-section-label">The solution</p><h2>One evidence chain, from observation to action.</h2></div><ol><li><span>01</span><strong>Observe change</strong><p>Bring vegetation, rainfall, heat and soil-moisture evidence into one comparable view.</p></li><li><span>02</span><strong>Detect persistence</strong><p>Identify active satellite-observed drought episodes consistently across every ADM1.</p></li><li><span>03</span><strong>Estimate continuation</strong><p>Compare experimental ML with historical reference at 30, 60, 90 and 180 days.</p></li></ol></section>

    <section className="landing-capabilities" aria-labelledby="capabilities-title"><p className="landing-section-label">Three capabilities</p><h2 id="capabilities-title">Monitor. Anticipate. Act.</h2><div><article><strong>IGAD-wide monitoring</strong><p>A consistent satellite condition assessment for 121 ADM1 areas across eight countries.</p></article><article><strong>Persistent episode outlooks</strong><p>Continuation estimates with horizon, evidence, freshness and historical context kept visible.</p></article><article><strong>Action-ready evidence</strong><p>Prioritized alerts and recommendations without hiding uncertainty or data limitations.</p></article></div></section>

    <section className="landing-pilots" id="pilots"><div><p className="landing-section-label">Current coverage</p><h2>Eight countries. 121 ADM1 areas. One method.</h2><p>Every area is evaluated for an active satellite-observed drought condition. Active episodes receive continuation estimates; inactive areas remain explicitly not applicable.</p><a href="/overview?layer=episodes">View persistent episodes →</a></div><div className="landing-terrain" aria-hidden="true"><span>121 ADM1 evaluated</span><span>30–180 day outlooks</span></div></section>

    <section className="landing-limitations"><p className="landing-section-label">Use responsibly</p><h2>A decision-support prototype, not an official warning service.</h2><p>ML estimates are experimental and shown beside a historical reference. Coverage, data latency and aggregation affect interpretation; validate recommendations with current field information and local expertise.</p><a href="/about/provenance">Read data provenance →</a></section>

    <section className="landing-final"><p>Mwangaza</p><h2>Find the drought episodes most likely to persist.</h2><div className="landing-actions">{ctas.slice(0, 2).map(cta => <a className={cta.primary ? "primary" : "secondary"} href={cta.href} key={cta.key}>{cta.label}</a>)}</div></section>
    <footer className="landing-footer"><span>IGAD Hackathon prototype · 2026</span><a href="/about">Methodology and limitations</a></footer>
  </main>;
}
