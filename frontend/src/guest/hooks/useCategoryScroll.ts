import { RefObject, useEffect, useState } from "react";

export function useCategoryScroll(sectionRefs: Map<number, RefObject<HTMLDivElement>>, initialId: number) {
  const [activeId, setActiveId] = useState(initialId);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const active = entries.find((entry) => entry.isIntersecting);
        if (active?.target instanceof HTMLElement) {
          const id = Number(active.target.dataset.categoryId);
          if (id) setActiveId(id);
        }
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: 0.1 },
    );

    sectionRefs.forEach((ref) => {
      if (ref.current) observer.observe(ref.current);
    });

    return () => observer.disconnect();
  }, [sectionRefs]);

  return { activeId, setActiveId };
}
