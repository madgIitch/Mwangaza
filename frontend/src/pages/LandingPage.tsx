import type { LandingLinks } from "../config/landing";
import { landingLinks, validPublicUrl } from "../config/landing";

export function LandingPage({ links = landingLinks }: { links?: LandingLinks }): JSX.Element {
  const ctas = [
    { key: "dashboard", label: "Open dashboard", href: links.dashboard, primary: true },
    { key: "demo", label: "Explore the demo", href: links.demo, primary: false },
    { key: "github", label: "View on GitHub", href: links.github, primary: false }
  ].filter(item => validPublicUrl(item.href));
  return <main className="landing-page">
    <header className="landing-nav"><a className="landing-wordmark" href="/landing">Mwangaza</a><nav aria-label="Landing navigation"><a href="#approach">How it works</a><a href="#pilots">Pilots</a><a href="/about">About</a></nav></header>
    <section className="landing-hero">
      <img src="/landing/hero-northern-kenya.png" alt="Aerial view of a braided dry riverbed across semi-arid Northern Kenya at dawn" />
      <div className="landing-hero-shade" />
      <div className="landing-hero-copy">
        <p className="landing-kicker">Satellite evidence for anticipatory action</p>
        <h1><span>Mwangaza</span>Bringing Light to Early Action</h1>
        <p>See drought conditions earlier, understand the evidence, and prepare local action with transparent data provenance.</p>
        <div className="landing-actions">{ctas.map(cta => <a className={cta.primary ? "primary" : "secondary"} href={cta.href} key={cta.key}>{cta.label}</a>)}</div>
      </div>
      <a className="landing-scroll" href="#problem">Scroll to understand <span aria-hidden="true">↓</span></a>
    </section>

    <section className="landing-problem" id="problem"><p className="landing-section-label">The problem</p><h2>Drought signals arrive before decisions do.</h2><p>Satellite and climate observations are abundant, but local teams still need a clear, traceable view of where conditions are worsening and what should be reviewed next.</p></section>

    <section className="landing-approach" id="approach"><div><p className="landing-section-label">The solution</p><h2>One evidence chain, from observation to action.</h2></div><ol><li><span>01</span><strong>Observe change</strong><p>Bring vegetation, rainfall and surface-temperature evidence into one seasonal view.</p></li><li><span>02</span><strong>Explain risk</strong><p>Keep quality, source and contribution visible alongside every composite signal.</p></li><li><span>03</span><strong>Prepare action</strong><p>Connect persistent episodes and alerts with clear early-action recommendations.</p></li></ol></section>

    <section className="landing-capabilities" aria-labelledby="capabilities-title"><p className="landing-section-label">Three capabilities</p><h2 id="capabilities-title">Monitor. Interpret. Act.</h2><div><article><strong>Environmental monitoring</strong><p>Seasonally comparable vegetation, rainfall and heat signals.</p></article><article><strong>Transparent risk</strong><p>Quality-aware scores with provenance and explicit demo states.</p></article><article><strong>Early-action workflow</strong><p>Persistent episodes, alerts and recommended actions in one operational view.</p></article></div></section>

    <section className="landing-pilots" id="pilots"><div><p className="landing-section-label">Current pilots</p><h2>Regional context. Local focus.</h2><p>Somalia demonstrates a national-to-pilot scenario. Northern Kenya compares Turkana, Marsabit and Isiolo through the same offline evidence chain.</p><a href="/region">Explore Regions →</a></div><div className="landing-terrain" aria-hidden="true"><span>Somalia</span><span>Northern Kenya</span></div></section>

    <section className="landing-limitations"><p className="landing-section-label">Use responsibly</p><h2>A decision-support prototype, not an official warning service.</h2><p>Coverage, clouds, data latency and aggregation affect interpretation. Exposure means potentially exposed population, not confirmed impact. Validate recommendations with current field information and local expertise.</p><a href="/about/provenance">Read data provenance →</a></section>

    <section className="landing-final"><p>Mwangaza</p><h2>Turn earlier evidence into earlier review.</h2><div className="landing-actions">{ctas.slice(0, 2).map(cta => <a className={cta.primary ? "primary" : "secondary"} href={cta.href} key={cta.key}>{cta.label}</a>)}</div></section>
    <footer className="landing-footer"><span>IGAD Hackathon prototype · 2026</span><a href="/about">Methodology and limitations</a></footer>
  </main>;
}
