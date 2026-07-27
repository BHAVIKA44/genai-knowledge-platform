import { motion, useReducedMotion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, BookOpenText, Check, Search } from "lucide-react";

export function ProductHeader() {
  return (
    <header className="product-header">
      <a className="wordmark" href="#top" aria-label="GenAI Knowledge Platform home">
        <span className="wordmark-mark" aria-hidden="true" />
        GenAI Knowledge Platform
      </a>
      <nav aria-label="Main navigation">
        <a href="#add-knowledge">Add knowledge</a>
        <a href="#search">Search</a>
        <a href="#how-it-works">How it works</a>
      </nav>
      <a className="header-action" href="#add-knowledge">
        Add a resource <ArrowUpRight size={14} aria-hidden="true" />
      </a>
    </header>
  );
}

export function EditorialHero() {
  const reducedMotion = useReducedMotion();
  const transition = reducedMotion ? { duration: 0 } : { duration: 0.6, ease: "easeOut" as const };
  return (
    <section className="hero" id="top" aria-labelledby="hero-heading">
      <motion.div
        className="hero-copy"
        initial={{ opacity: 0, y: reducedMotion ? 0 : 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={transition}
      >
        <p className="section-kicker">GenAI Knowledge Platform</p>
        <h1 id="hero-heading">
          Build knowledge <em>you can rely on.</em>
        </h1>
        <p className="hero-description">
          Add papers, guides, and learning resources. Every source is reviewed before it becomes
          part of your searchable GenAI knowledge base.
        </p>
        <div className="hero-actions">
          <a className="button button-primary" href="#add-knowledge">
            Add a resource <ArrowDownRight size={17} aria-hidden="true" />
          </a>
          <a className="button button-quiet" href="#search">
            Search your knowledge
          </a>
        </div>
      </motion.div>
      <KnowledgeVisual />
      <p className="hero-caption">A calmer way to grow what you know.</p>
    </section>
  );
}

export function KnowledgeVisual() {
  const reducedMotion = useReducedMotion();
  return (
    <motion.div
      className="knowledge-visual"
      initial={{ opacity: 0, scale: reducedMotion ? 1 : 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: reducedMotion ? 0 : 0.8, delay: reducedMotion ? 0 : 0.12 }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 620 620" role="presentation">
        <defs>
          <radialGradient id="orb" cx="50%" cy="40%" r="58%">
            <stop offset="0" stopColor="#78b8ff" stopOpacity=".72" />
            <stop offset=".45" stopColor="#2177ee" stopOpacity=".25" />
            <stop offset="1" stopColor="#07101f" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="line" x1="0" x2="1">
            <stop stopColor="#9ed0ff" stopOpacity=".08" />
            <stop offset=".5" stopColor="#82c3ff" stopOpacity=".9" />
            <stop offset="1" stopColor="#9ed0ff" stopOpacity=".08" />
          </linearGradient>
        </defs>
        <circle cx="310" cy="310" r="274" fill="url(#orb)" />
        <circle className="visual-ring visual-ring-one" cx="310" cy="310" r="213" />
        <circle className="visual-ring visual-ring-two" cx="310" cy="310" r="150" />
        <path d="M96 376C171 261 236 426 303 284S440 301 528 178" stroke="url(#line)" />
        <path d="M98 218C182 329 238 167 332 265S433 423 531 349" stroke="url(#line)" />
        {["120,360", "189,276", "303,284", "391,225", "478,271", "528,178", "332,265"].map(
          (point) => {
            const [cx, cy] = point.split(",");
            return <circle key={point} className="visual-node" cx={cx} cy={cy} r="5" />;
          },
        )}
      </svg>
      <div className="visual-document" />
    </motion.div>
  );
}

const story = [
  ["01", "Add a resource", "Bring in a GenAI paper, guide, or note."],
  ["02", "Understand the content", "We read the material and identify what it teaches."],
  ["03", "Review its quality", "Clarity, relevance, and incomplete explanations are surfaced."],
  [
    "04",
    "Check references when useful",
    "Time-sensitive claims can be compared with external evidence.",
  ],
  ["05", "Make a clear decision", "The resource is added, paused for your input, or kept out."],
  ["06", "Search trusted knowledge", "Only accepted material becomes part of your library."],
] as const;

export function KnowledgeStory() {
  const reducedMotion = useReducedMotion();
  return (
    <section className="knowledge-story" id="how-it-works" aria-labelledby="story-heading">
      <div className="story-intro">
        <p className="section-kicker">How it works</p>
        <h2 id="story-heading">
          What deserves <em>to be remembered?</em>
        </h2>
      </div>
      <div className="story-steps">
        {story.map(([number, title, description], index) => (
          <motion.article
            className="story-step"
            key={number}
            initial={{ opacity: 0, y: reducedMotion ? 0 : 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{
              duration: reducedMotion ? 0 : 0.45,
              delay: reducedMotion ? 0 : index * 0.03,
            }}
          >
            <span>{number}</span>
            <div>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
            {index === 5 ? <Search aria-hidden="true" /> : <BookOpenText aria-hidden="true" />}
          </motion.article>
        ))}
      </div>
    </section>
  );
}

export function EditorialFooter() {
  return (
    <footer className="editorial-footer">
      <p className="section-kicker">Start with a source</p>
      <h2>
        Your knowledge base <em>should know better.</em>
      </h2>
      <p>Build a library of GenAI learning material you can return to with confidence.</p>
      <a className="button button-primary" href="#add-knowledge">
        Add your first resource <Check size={17} aria-hidden="true" />
      </a>
    </footer>
  );
}
