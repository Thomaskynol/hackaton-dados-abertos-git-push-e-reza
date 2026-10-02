/**
 * Tipos geográficos do Mapa (camada de desenho, não de dados agrícolas).
 * Nenhum número agrícola aqui — só contornos + nomes oficiais (IBGE).
 */
export interface MunicipioGeo {
  ibge: string;
  nome: string;
  /** Anéis [lng,lat] simplificados, prontos para projetar em SVG path. */
  aneis: [number, number][][];
}

export interface MalhaMunicipios {
  uf: string;
  fonte: string;
  gerado_em: string;
  total: number;
  municipios: MunicipioGeo[];
}
