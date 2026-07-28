import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import digitalHumanHead from "../assets/digital-human-head.png";

type HudCallout = {
  className: string;
  delay: number;
  floatClassName: string;
  text: string;
};

const callouts: readonly HudCallout[] = [
  {
    className: "hud-callout-forehead",
    delay: 0.56,
    floatClassName: "hud-callout-float-1",
    text: "OBSESSED WITH HARNESSING\nMULTI-AGENT SWARMS\n& LLM ORCHESTRATION",
  },
  {
    className: "hud-callout-brain",
    delay: 0.68,
    floatClassName: "hud-callout-float-2",
    text: "MAPPING KNOWLEDGE INTO\nHIGH-DIMENSIONAL VECTOR DBs",
  },
  {
    className: "hud-callout-eye",
    delay: 0.8,
    floatClassName: "hud-callout-float-3",
    text: "SPOTS MODEL HALLUCINATIONS\nIN MILLISECONDS",
  },
  {
    className: "hud-callout-mouth",
    delay: 0.92,
    floatClassName: "hud-callout-float-4",
    text: "SPEAKS IN EMBEDDINGS,\nCHUNK SIZES &\nCOSINE SIMILARITY",
  },
];

function HudCallout({ callout }: { callout: HudCallout }) {
  const reducedMotion = useReducedMotion();

  return (
    <motion.p
      className={`hud-callout ${callout.className}`}
      initial={{ opacity: 0, y: reducedMotion ? 0 : 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reducedMotion ? 0 : 0.28, delay: reducedMotion ? 0 : callout.delay }}
    >
      <span className={`hud-callout-float ${callout.floatClassName}`}>{callout.text}</span>
    </motion.p>
  );
}

export function DigitalHumanVisual() {
  const reducedMotion = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const imageOffset = useTransform(scrollYProgress, [0, 0.35], [0, -14]);
  const hudOffset = useTransform(scrollYProgress, [0, 0.35], [0, -24]);

  return (
    <motion.figure
      className="digital-human-visual"
      initial={{ opacity: 0, scale: reducedMotion ? 1 : 0.975 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: reducedMotion ? 0 : 0.64, delay: reducedMotion ? 0 : 0.52 }}
    >
      <div className="digital-human-image-stage" aria-hidden="true">
        <div className="digital-human-image-float">
          <motion.img
            className="digital-human-image"
            src={digitalHumanHead}
            alt=""
            style={{ y: reducedMotion ? 0 : imageOffset }}
          />
        </div>
        <span className="bust-scanline-track" aria-hidden="true">
          <span className="bust-scanline" />
        </span>
      </div>
      <motion.div className="digital-human-hud" style={{ y: reducedMotion ? 0 : hudOffset }}>
        <svg
          className="hud-connectors"
          viewBox="0 0 100 100"
          aria-hidden="true"
          preserveAspectRatio="none"
        >
          <path d="M36 23V26H43L48 31" />
          <path d="M65 31H62V36H59" />
          <path d="M65 54H61V50H57" />
          <path d="M34 63H42L47 63" />
          <circle className="hud-terminal" cx="48" cy="31" r="0.48" />
          <circle className="hud-terminal" cx="59" cy="38" r="0.48" />
          <circle className="hud-terminal" cx="57" cy="49" r="0.48" />
          <circle className="hud-terminal" cx="47" cy="63" r="0.48" />
        </svg>
        {callouts.map((callout) => (
          <HudCallout key={callout.className} callout={callout} />
        ))}
        <motion.span
          className="target-reticle"
          initial={{ opacity: 0, scale: reducedMotion ? 1 : 0.7 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: reducedMotion ? 0 : 0.3, delay: reducedMotion ? 0 : 1.1 }}
          aria-hidden="true"
        >
          [ CLICK ]
        </motion.span>
      </motion.div>
      <div className="mobile-hud-details">
        <p>{callouts[0].text}</p>
        <p>{callouts[3].text}</p>
      </div>
      <motion.figcaption
        initial={{ opacity: 0, y: reducedMotion ? 0 : 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.3, delay: reducedMotion ? 0 : 1.2 }}
      >
        Is this you?
      </motion.figcaption>
    </motion.figure>
  );
}
