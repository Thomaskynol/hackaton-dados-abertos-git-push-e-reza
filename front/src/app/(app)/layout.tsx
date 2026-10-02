import { TopBar } from "@/components/TopBar";
import { BottomNav } from "@/components/BottomNav";

/** Casca das telas internas: barra superior + conteúdo + navegação inferior. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 pb-28 md:pb-12 pt-4 md:pt-6 flex-1">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
