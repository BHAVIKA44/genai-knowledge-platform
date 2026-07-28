import { motion, useReducedMotion } from "framer-motion";
import { BookOpenText, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { DigitalHumanVisual } from "./DigitalHumanVisual";

const navigationItems = [
  ["how-it-works", "How It Works"],
  ["search", "Search"],
  ["add-knowledge", "Add Knowledge"],
] as const;

const heroHeadlineLines = [
  "One place to learn,",
  "share, and grow your",
  "GenAI knowledge.",
] as const;

export function ProductHeader() {
  const [activeSection, setActiveSection] = useState<string | null>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visibleSection = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];

        if (visibleSection) setActiveSection(visibleSection.target.id);
      },
      { rootMargin: "-35% 0px -50%", threshold: [0.1, 0.35, 0.6] },
    );

    navigationItems.forEach(([id]) => {
      const section = document.getElementById(id);
      if (section) observer.observe(section);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <header className="product-header">
      <a className="wordmark" href="#top" aria-label="GenAI Knowledge Platform home">
        <span className="wordmark-mark" aria-hidden="true" />
        <span className="wordmark-label">GenAI Knowledge Platform</span>
      </a>
      <nav aria-label="Main navigation">
        {navigationItems.map(([id, label]) => (
          <a
            key={id}
            href={`#${id}`}
            className={activeSection === id ? "is-active" : undefined}
            aria-current={activeSection === id ? "location" : undefined}
            onClick={() => setActiveSection(id)}
          >
            {label}
          </a>
        ))}
      </nav>
    </header>
  );
}

export function EditorialHero() {
  const reducedMotion = useReducedMotion();
  const revealInitial = reducedMotion ? { opacity: 0 } : { opacity: 0, y: 22, filter: "blur(8px)" };
  const revealAnimate = reducedMotion ? { opacity: 1 } : { opacity: 1, y: 0, filter: "blur(0px)" };
  const revealTransition = (delay: number) => ({
    duration: reducedMotion ? 0 : 0.48,
    delay: reducedMotion ? 0 : delay,
    ease: "easeOut" as const,
  });

  return (
    <section className="hero" id="top" aria-labelledby="hero-heading">
      <div className="hero-copy">
        <h1 id="hero-heading">
          <span className="sr-only">One place to learn, share, and grow your GenAI knowledge.</span>
          <span className="hero-headline-lines" aria-hidden="true">
            {heroHeadlineLines.map((line, index) => (
              <motion.span
                key={line}
                className="hero-headline-line"
                initial={revealInitial}
                animate={revealAnimate}
                transition={revealTransition(0.1 + index * 0.11)}
              >
                {line}
              </motion.span>
            ))}
          </span>
        </h1>
        <motion.p
          className="hero-trust"
          initial={revealInitial}
          animate={revealAnimate}
          transition={revealTransition(0.66)}
        >
          Every contribution is reviewed before it becomes searchable.
        </motion.p>
      </div>
      <DigitalHumanVisual />
    </section>
  );
}

const story = [
  ["01", "You add a resource", "Share a paper, guide, or note that helped you learn."],
  ["02", "We understand the content", "We identify what the resource can teach the community."],
  ["03", "We review the quality", "We look for clarity, relevance, and useful context."],
  [
    "04",
    "We check important claims",
    "When useful, we compare changing information with references.",
  ],
  [
    "05",
    "We ask for your input when needed",
    "You stay in control when a resource needs a quick decision.",
  ],
  ["06", "We add trusted knowledge", "Accepted resources become part of the community library."],
] as const;

export function KnowledgeStory() {
  const reducedMotion = useReducedMotion();
  return (
    <section className="knowledge-story" id="how-it-works" aria-labelledby="story-heading">
      <motion.div
        className="story-intro"
        initial={{
          opacity: 0,
          y: reducedMotion ? 0 : 20,
          filter: reducedMotion ? undefined : "blur(6px)",
        }}
        whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        viewport={{ once: true, amount: 0.35 }}
        transition={{ duration: reducedMotion ? 0 : 0.45, ease: "easeOut" }}
      >
        <h2 id="story-heading">How trusted knowledge reaches the platform</h2>
      </motion.div>
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
