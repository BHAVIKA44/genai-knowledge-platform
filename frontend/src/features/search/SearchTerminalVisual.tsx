import { motion, useReducedMotion } from "framer-motion";

const screenAscii = String.raw`
@#%&:: 4v qwy 01 7F Jse :: /\\|_+= @#%&:: 4v qwy 01 7F Jse :: /\\|_+=
  01 7F Jse :: @#%& /\\|_+= :: 4v qwy 01 7F Jse :: @#%& /\\|_+=
@#%&:: /\\|_+= 4v qwy 01 7F Jse :: @#%&:: /\\|_+= 4v qwy 01 7F Jse
  qwy 01 7F Jse :: @#%& /\\|_+= :: qwy 01 7F Jse :: @#%& /\\|_+=
@#%&:: 4v qwy 01 7F Jse :: /\\|_+= @#%&:: 4v qwy 01 7F Jse :: /\\|_+=
  01 7F Jse :: @#%& /\\|_+= :: 4v qwy 01 7F Jse :: @#%& /\\|_+=
`;

const ambientAscii = String.raw`
    @ # % & :: 4v qwy 01 7F Jse /\\ | _ + = @ # % & :: 4v qwy 01 7F Jse
  :: 4v qwy 01 7F Jse @ # % & /\\ | _ + = :: 4v qwy 01 7F Jse @ # % &
    @ # % & :: 4v qwy 01 7F Jse /\\ | _ + = @ # % & :: 4v qwy 01 7F Jse
`;

export function SearchTerminalVisual() {
  const reducedMotion = useReducedMotion();

  return (
    <motion.aside
      className="search-workspace-visual"
      initial={{ opacity: 0, y: reducedMotion ? 0 : 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: reducedMotion ? 0 : 0.45, ease: "easeOut" }}
      aria-hidden="true"
    >
      <div className="workspace-ambient" />
      <motion.pre
        className="workspace-code workspace-code-ambient"
        animate={reducedMotion ? undefined : { y: [0, -4, 0] }}
        transition={{ duration: 16, ease: "easeInOut", repeat: Infinity }}
      >
        {ambientAscii}
      </motion.pre>
      <div className="developer-monitor">
        <div className="monitor-screen">
          <div className="terminal-panel">
            <div className="terminal-bar">
              <span />
              <span />
              <span />
            </div>
            <motion.pre
              className="workspace-code workspace-code-screen"
              animate={reducedMotion ? undefined : { y: [0, 3, 0] }}
              transition={{ duration: 14, ease: "easeInOut", repeat: Infinity }}
            >
              {screenAscii}
            </motion.pre>
          </div>
        </div>
        <div className="monitor-stand" />
      </div>
      <div className="workspace-desk">
        <div className="workspace-keyboard" />
        <div className="workspace-mousepad" />
      </div>
    </motion.aside>
  );
}
