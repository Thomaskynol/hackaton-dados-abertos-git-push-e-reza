/**
 * Logo oficial do AgroPilot (fonte: src/assets/logo/logo-agropilot.svg).
 *
 * Dois usos:
 *  - <LogoMarca/>   : só o símbolo (folha germinando no mostrador), para
 *                     cabeçalhos pequenos ao lado do texto "AgroPilot".
 *  - <LogoCompleta/>: a marca inteira com o nome e o slogan, para telas de
 *                     entrada (login/signup/abertura), onde há espaço.
 *
 * SVG inline (não <img>) para herdar cor, ficar nítido em qualquer tamanho e
 * não depender de request de rede.
 */

/** Símbolo da marca — folha germinando no mostrador. Quadrado, escala por `size`. */
export function LogoMarca({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="60 24 200 160"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="AgroPilot"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="agp-leaf" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#65C987" />
          <stop offset="100%" stopColor="#C4F26B" />
        </linearGradient>
      </defs>
      <circle cx="160" cy="100" r="68" fill="#142F24" stroke="#315548" strokeWidth="2" />
      <circle cx="160" cy="100" r="57" fill="none" stroke="#527C60" strokeWidth="1.5" strokeDasharray="3 7" />
      <path d="M160 135 L160 83" stroke="#B8E986" strokeWidth="5" strokeLinecap="round" />
      <path d="M160 105 C137 105 119 91 119 69 C143 68 160 82 160 105Z" fill="url(#agp-leaf)" />
      <path d="M160 88 C160 65 178 48 202 50 C202 74 185 89 160 88Z" fill="url(#agp-leaf)" />
      <path d="M160 105 C173 99 185 87 195 66" fill="none" stroke="#0B1F18" strokeWidth="2" strokeLinecap="round" />
      <path d="M160 105 C150 91 139 83 127 77" fill="none" stroke="#0B1F18" strokeWidth="2" strokeLinecap="round" />
      <path d="M142 135 L178 135" stroke="#B8E986" strokeWidth="4" strokeLinecap="round" />
      <path d="M160 24 L160 33 M160 167 L160 176 M84 100 L93 100 M227 100 L236 100" stroke="#B8E986" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M213 45 L220 38 L223 48 L233 51 L223 55 L220 65 L216 55 L206 51Z" fill="#C4F26B" />
    </svg>
  );
}

/** Marca completa com nome e slogan — para telas de entrada. */
export function LogoCompleta({ width = 200, className = "" }: { width?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 320 250"
      width={width}
      className={className}
      role="img"
      aria-label="AgroPilot — decisões mais inteligentes"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="agp-leaf-full" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#65C987" />
          <stop offset="100%" stopColor="#C4F26B" />
        </linearGradient>
      </defs>
      <circle cx="160" cy="100" r="68" fill="#142F24" stroke="#315548" strokeWidth="2" />
      <circle cx="160" cy="100" r="57" fill="none" stroke="#527C60" strokeWidth="1.5" strokeDasharray="3 7" />
      <path d="M160 135 L160 83" stroke="#B8E986" strokeWidth="5" strokeLinecap="round" />
      <path d="M160 105 C137 105 119 91 119 69 C143 68 160 82 160 105Z" fill="url(#agp-leaf-full)" />
      <path d="M160 88 C160 65 178 48 202 50 C202 74 185 89 160 88Z" fill="url(#agp-leaf-full)" />
      <path d="M160 105 C173 99 185 87 195 66" fill="none" stroke="#0B1F18" strokeWidth="2" strokeLinecap="round" />
      <path d="M160 105 C150 91 139 83 127 77" fill="none" stroke="#0B1F18" strokeWidth="2" strokeLinecap="round" />
      <path d="M142 135 L178 135" stroke="#B8E986" strokeWidth="4" strokeLinecap="round" />
      <path d="M160 24 L160 33 M160 167 L160 176 M84 100 L93 100 M227 100 L236 100" stroke="#B8E986" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M213 45 L220 38 L223 48 L233 51 L223 55 L220 65 L216 55 L206 51Z" fill="#C4F26B" />
      <text x="160" y="207" textAnchor="middle" fill="#F2F7EF" fontSize="36" fontWeight="800" letterSpacing="1.5" fontFamily="Arial, Helvetica, sans-serif">
        AGRO<tspan fill="#B8E986">PILOT</tspan>
      </text>
      <text x="160" y="230" textAnchor="middle" fill="#A9C4B4" fontSize="10" letterSpacing="3.2" fontFamily="Arial, Helvetica, sans-serif">
        DECISÕES MAIS INTELIGENTES
      </text>
    </svg>
  );
}
