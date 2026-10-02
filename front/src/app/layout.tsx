import type { Metadata, Viewport } from "next";
import "./globals.css";
import { PerfilProvider } from "@/lib/perfil-context";

/*
  Fontes: usamos a stack do sistema (definida em globals.css) para não depender
  de rede no build/offline. As vars --font-sans/--font-display continuam valendo
  no Tailwind; é só trocar por next/font quando houver acesso garantido à CDN.
*/

export const metadata: Metadata = {
  title: "AgroPilot — seu copiloto da roça",
  description:
    "Copiloto da safra para o pequeno produtor. Transforma dados públicos (ZARC, Agrofit, ANA) em o próximo passo no campo.",
  applicationName: "AgroPilot",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#C85A3C",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("agropilot:tema");if(t==="dark"||(!t&&window.matchMedia("(prefers-color-scheme: dark)").matches)){document.documentElement.classList.add("dark")}}catch(e){}})()`,
          }}
        />
      </head>
      <body>
        <PerfilProvider>{children}</PerfilProvider>
      </body>
    </html>
  );
}
