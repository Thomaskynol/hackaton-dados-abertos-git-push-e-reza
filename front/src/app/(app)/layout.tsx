import { TopBar } from "@/components/TopBar";
import { BottomNav } from "@/components/BottomNav";

/** Casca das telas internas: barra superior + conteúdo + navegação inferior. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas">
      <TopBar />
      <main className="mx-auto max-w-md px-4 pb-28 pt-4">{children}</main>
      <BottomNav />
    </div>
  );
}
