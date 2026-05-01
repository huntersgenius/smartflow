import { motion } from "framer-motion";
import type { ReactNode } from "react";

export default function BottomSheet({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ y: 80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 80, opacity: 0 }}
      className="fixed inset-x-0 bottom-0 z-40 mx-auto w-full max-w-[430px] rounded-t-2xl border border-sf-line bg-white p-4 shadow-soft"
    >
      <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-slate-200" />
      {children}
    </motion.div>
  );
}
