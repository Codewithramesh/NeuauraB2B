import { useState } from "react";
import { Lightbulb } from "lucide-react";
import { useResource } from "./useResource";
import { SectionTitle, ErrorNotice, Empty, InsightCard } from "./ui";
import { human } from "./api";
import type { Insight } from "./types";

export function InsightsPage({ onOpen }: { onOpen: (id: string) => void }) {
  const { data, error } = useResource<Insight[]>("/insights");
  const [filter, setFilter] = useState("all");
  const filtered = data?.filter(
    (i) => filter === "all" || i.sentiment === filter,
  );
  return (
    <>
      <SectionTitle
        eyebrow="CONNECT THE DOTS"
        title="Business insights"
        description="Find the signals in your everyday conversations."
      />
      <div className="tabs">
        {["all", "positive", "negative", "neutral"].map((s) => (
          <button
            className={filter === s ? "selected" : ""}
            key={s}
            onClick={() => setFilter(s)}
          >
            {s === "all" ? "All insights" : human(s)}
          </button>
        ))}
      </div>
      <ErrorNotice message={error} />
      <section className="panel">
        {filtered?.length ? (
          filtered.map((i) => (
            <InsightCard key={i.id} insight={i} onOpen={onOpen} />
          ))
        ) : (
          <Empty
            icon={Lightbulb}
            title="A fresh perspective is on its way"
            description="Insights from successfully processed conversations will appear here, with direct links to their evidence."
          />
        )}
      </section>
    </>
  );
}
