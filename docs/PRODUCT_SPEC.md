# 🌾 AgroPilot — Copiloto Agrícola 24/7

## Documento de Definição do Produto (PRD) & Arquitetura Técnica — Hackathon 2026

---

## 1. Filosofia e Princípios Fundamentais

### O princípio que guia tudo

> *"O pequeno produtor não pode errar. Ele não tem margem para errar."*

Um grande produtor pode perder 10% da safra e ainda fechar o ano no azul. Um pequeno produtor que perde 10% pode não conseguir pagar as contas, alimentar a família, ou plantar no ano seguinte.

*Toda decisão de produto do AgroPilot parte dessa premissa.*

### Os 6 princípios do AgroPilot

| Princípio | Significado | Implementação no Produto |
|---|---|---|
| **1. Universal** | Funciona para soja, café, cana, milho, mandioca, feijão, hortaliças | Base de conhecimento modular por cultura, ciclo fenológico e solo |
| **2. Proativo** | Não espera o produtor perguntar — avisa antes do problema acontecer | Motor de monitoramento contínuo com triggers de clima, pragas e janelas |
| **3. Personalizado** | Cada recomendação é baseada na realidade específica daquele produtor | Contexto dinâmico: Talhão, tipo de solo, estágio fenológico e histórico |
| **4. Explicável** | Toda recomendação mostra o porquê, a fonte e a confiança | Box de transparência: Fonte (ex: ZARC/Embrapa), Causa e Nível de Confiança |
| **5. Seguro** | Nunca substitui o Zarc, nunca receita defensivos sem agrônomo, mostra incerteza | Salvaguardas éticas, alertas de risco ZARC e conformidade Proagro/Pronaf |
| **6. Acessível** | Cadastro com telefone + nome. Interface conversacional e áudio | Estilo WhatsApp, suporte a áudio transcrito, linguagem simples e direta |

---

### O que o AgroPilot NÃO é

| Não é | Por quê |
|---|---|
| ❌ **Um site informativo** | Isso qualquer um acessa no Google sem contexto prático. |
| ❌ **Um dashboard bonito sem ação** | O produtor não quer apenas gráficos de séries temporais; quer saber **o que fazer hoje**. |
| ❌ **Um ChatGPT agrícola genérico** | Modelos genéricos não conhecem o Zarc decendial, microclima de radar nem os dados da gleba. |
| ❌ **Um app reativo que só responde perguntas** | O diferencial é a **proatividade**: avisar antes da geada, do veranico ou da eclosão da praga. |
| ❌ **Um sistema exclusivo para grandes produtores** | O foco é o pequeno e médio (agricultura familiar e médios cooperados), com escalabilidade. |

---

### O que o AgroPilot É

> **Um copiloto agrícola 24/7 que conhece o produtor, conhece a propriedade, conhece a região, e acompanha cada etapa — da compra da semente até a venda — alertando, orientando e prevenindo erros.**

---

## 2. Visão Geral do Sistema & Ciclo da Safra

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       JORNADA COMPLETA DO PRODUTOR                           │
│                                                                              │
│   🌱 COMPRAR         🌾 PLANTAR        💧 CUIDAR       🚜 COLHER    💰 VENDER │
│   SEMENTE            JANELA           MONITORAR       MOMENTO      CANAL     │
│      │                  │                │               │            │      │
│      ▼                  ▼                ▼               ▼            ▼      │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                         AGROPILOT 24/7                               │   │
│   │  • Qual semente?    • Quando?        • Clima 24/7?   • Ponto umid?• Onde?│   │
│   │  • Qual cultivar?   • Solo apto?     • Praga/Fungo?  • Chuva colh?• Preço│   │
│   │  • Conform. ZARC?   • Risco decêndio?• Nutrição?     • Logística? • Canal│   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│               NOTIFICAÇÕES DIÁRIAS & ALERTAS PUSH PROATIVOS                  │
│               MISSÕES DE CAMPO PRÁTICAS PASSO A PASSO                        │
│               COPILOTO CONVERSACIONAL VIA WHATSAPP / WEB                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. As 7 Capacidades Centrais

1. **Entender o Produtor:** Onboarding conversacional em menos de 2 minutos (Nome, Telefone, Município, Cultura atual e tamanho da área em hectares).
2. **Conhecer a Região:** Mapeamento de coordenadas, classificação de solo (Argiloso AD3, Médio AD2, Arenoso AD1), microclima INMET/CPTEC e histórico fitossanitário.
3. **Planejar a Safra (ZARC):** Zoneamento Agrícola de Risco Climático oficial. Identificação de decêndios com risco < 20% (Apto para crédito Proagro/Pronaf) e janelas desfavoráveis.
4. **Monitorar 24/7 Proativamente:** Algoritmo que roda em background cruzando previsões de 1 a 15 dias com a fase fenológica da planta (ex: florada sensível a estresse térmico, formação de grão sensível a veranico).
5. **Orientar Decisões:** Suporte a crédito rural (Pronaf B, Custeio), orientações sobre defensivos biológicos e manejo integrado de pragas (MIP), indicação de agrônomo responsável.
6. **Executar Ações (Missões de Campo):** Transforma dados complexos em checklists acionáveis (ex: *"Missão #14: Vistoriar 10 plantas na baixada para verificar ferrugem asiática"*).
7. **Acompanhar até a Venda:** Monitor de cotações em tempo real (Cepea, Conab, cooperativas locais), canais de venda direta (feiras, PAA, PNAE) e cálculo de margem líquida.

---

## 4. Arquitetura da Aplicação (Hackathon Demo)

- **Frontend:** Single Page Application rica, ultra-responsiva, desenvolvida em HTML5 semântico, Vanilla CSS com design tokens modernos (Dark/Light mode, Glassmorphism, Micro-animações), e JavaScript ES6+.
- **Engine Copiloto:** Agente conversacional agrícola treinado em regras agronômicas, diretrizes da Embrapa e ZARC decendial.
- **Motor de Simulação de Alertas:** Capacidade de acionar cenários reais para a banca do hackathon (Alerta de Geada, Onda de Calor no Florescimento, Eclosão de Praga, Janela ZARC Fechando).
- **Acessibilidade:** Botão de síntese de voz (ouvir recomendações como no WhatsApp) e interface de alta legibilidade sob luz solar direta.
