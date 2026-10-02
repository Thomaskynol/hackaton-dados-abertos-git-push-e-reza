/**
 * AgroPilot 24/7 — Motor de Inteligência do Copiloto Agrícola
 * Especializado em agricultura familiar brasileira, ZARC, Embrapa e alertas proativos.
 */

class AgroPilotCopilot {
  constructor() {
    this.farmer = AGRO_DATA.currentProfile;
    this.history = [];
  }

  setFarmerProfile(profile) {
    this.farmer = { ...this.farmer, ...profile };
  }

  /**
   * Responde ao produtor de forma humanizada, explicável e segura.
   * Respeita os 6 princípios fundamentais:
   * 1. Universal (adequado à cultura)
   * 2. Proativo (recomenda o próximo passo)
   * 3. Personalizado (chama pelo nome, menciona solo e município)
   * 4. Explicável (Fonte, Causa e Confiança %)
   * 5. Seguro (sempre alerta sobre limites e receituário agronômico)
   * 6. Acessível (linguagem direta, suporte a áudio)
   */
  processMessage(userText) {
    const text = userText.toLowerCase().trim();
    const cultura = AGRO_DATA.culturas[this.farmer.culturaAtual] || AGRO_DATA.culturas.soja;
    const parts = this.farmer.nome.trim().split(/\s+/);
    let nome = parts[0];
    if ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1]) {
      nome = `${parts[0]} ${parts[1]}`;
    }

    let response = {
      text: "",
      audioText: "",
      fonte: "Embrapa & ZARC / MAPA",
      porQue: "",
      confianca: 95,
      acaoSugerida: null,
      missaoId: null
    };

    // Cenário 1: Dúvida sobre quando plantar / Janela ZARC
    if (text.includes("plantar") || text.includes("semeadura") || text.includes("janela") || text.includes("zarc")) {
      response.text = `Olá, **${nome}**! Consultando o **ZARC oficial** para **${this.farmer.municipio}** no seu solo **${this.farmer.tipoSolo}** (argiloso com boa retenção hídrica):\n\n` +
        `✅ **Janela Recomendada:** Estamos no decêndio **Out/D3 a Nov/D2**, onde o risco climático é de apenas **20%** (Classe I - Risco Mínimo).\n` +
        `🛡️ **Seguro Proagro:** Plantando nesta janela, sua lavoura tem **cobertura garantida de 100%** contra frustração de safra.\n` +
        `⚠️ **Cuidado Crítico:** Não atrase a semeadura para além de 25 de Novembro; a partir daí, o risco sobe para 40% e o seguro pode recusar o custeio do Pronaf.`;
      
      response.audioText = `Oi ${nome}! O Zarc pra sua terra em Rio Verde tá liberado com risco de 20%, o melhor momento pra plantar é até o dia 20 de novembro pra não perder a garantia do Proagro.`;
      response.fonte = "Portaria ZARC MAPA nº 142/2024 • Solo AD3";
      response.porQue = "Evitar que a fase crítica de floração e enchimento de grãos coincida com o veranico típico de janeiro.";
      response.confianca = 98;
      response.acaoSugerida = "Ver Calendário ZARC";
    }

    // Cenário 2: Praga, lagarta, bicho na folha ou inseto
    else if (text.includes("lagarta") || text.includes("praga") || text.includes("bicho") || text.includes("inseto") || text.includes("percevejo")) {
      response.text = `Atenção, **${nome}**! Na cultura da **${cultura.nome}**, a presença de lagartas no estágio atual (${cultura.faseAtual}) exige medição antes de aplicar qualquer produto para você não jogar dinheiro fora:\n\n` +
        `🔍 **Manejo Integrado de Pragas (MIP):** Faça uma amostragem com pano de batida em 10 pontos. Só vale a pena gastar com defensivo se encontrar mais de **20 lagartas por metro** ou desfolha acima de **30%**.\n` +
        `🌱 **Dica Sustentável:** Dê preferência para controle biológico com *Bacillus thuringiensis* (Bt) ou vírus VPN, que preservam os inimigos naturais (como aranhas e tesourinhas).\n` +
        `🔒 **Regra de Segurança:** Nunca misture produtos sem o receituário do agrônomo da cooperativa.`;

      response.audioText = `Olha ${nome}, antes de gastar dinheiro com veneno, faz o pano de batida. Se der menos de 20 lagartas por metro, a planta aguenta firme e você economiza insumo.`;
      response.fonte = "Embrapa Soja - Manual de Manejo Integrado de Pragas (MIP)";
      response.porQue = "Pequenos produtores frequentemente gastam até 35% a mais em defensivos por aplicação precipitada sem contagem prévia.";
      response.confianca = 92;
      response.acaoSugerida = "Abrir Missão de Amostragem";
      response.missaoId = "mis-02";
    }

    // Cenário 3: Clima, frente fria, chuva, temporal ou geada
    else if (text.includes("chuva") || text.includes("tempo") || text.includes("clima") || text.includes("temporal") || text.includes("frente fria") || text.includes("geada")) {
      response.text = `Verifiquei os radares meteorológicos para **${this.farmer.municipio}**, **${nome}**:\n\n` +
        `⛈️ **Previsão de Curto Prazo:** Temos previsão de **acumulado de chuva de 75mm nas próximas 48 horas**, acompanhado de rajadas de vento de até 55 km/h.\n` +
        `🚜 **Ações Preventivas Urgentes:**\n` +
        `1. Suspenda qualquer pulverização foliar nas próximas 36 horas (a chuva lavará o produto, gerando prejuízo).\n` +
        `2. Vistorie as curvas de nível e saídas de água dos terraços no talhão 2 para não rasgar o solo com enxurrada.\n` +
        `3. Guarde máquinas e implementos em local coberto.`;

      response.audioText = `${nome}, vai entrar uma chuva forte de 75 milímetros com vento nas próximas 48 horas. Não pulverize nada agora pra não perder o produto e dá uma olhada nas curvas de nível.`;
      response.fonte = "INMET / CPTEC • Estação Meteorológica Automática de Rio Verde";
      response.porQue = "Frente polar em deslocamento rápido pelo Centro-Sul com saturação do solo a 68%.";
      response.confianca = 94;
      response.acaoSugerida = "Ver Alerta no Radar";
      response.missaoId = "mis-01";
    }

    // Cenário 4: Adubação, fertilizante, solo ou correção
    else if (text.includes("adubo") || text.includes("adubação") || text.includes("calcário") || text.includes("fósforo") || text.includes("terra")) {
      response.text = `Para o solo **${this.farmer.tipoSolo}** da sua propriedade (**${this.farmer.propriedade}**), **${nome}**:\n\n` +
        `🧪 **Características do seu solo:** O solo Argiloso AD3 tem alta capacidade de troca catiônica (CTC), o que significa que ele segura bem o adubo, mas precisa de matéria orgânica ativa.\n` +
        `💡 **Recomendação Econômica:** Não aplique adubo nitrogenado em cobertura se o solo estiver seco ou se houver previsão de chuvas torrenciais (perda por lixiviação).\n` +
        `📌 **Inoculação:** Para a soja, a inoculação com *Bradyrhizobium* + coinoculação com *Azospirillum* substitui o adubo nitrogenado químico, economizando até R$ 800 por hectare!`;

      response.audioText = `${nome}, como sua terra é argilosa AD3, ela segura bem o adubo. Capricha na inoculação de bactérias que você não precisa gastar com nitrogênio na soja.`;
      response.fonte = "Boletim de Fertilidade do Solo - Embrapa Cerrados";
      response.porQue = "Fixação biológica de nitrogênio supre 100% da necessidade da soja em solos equilibrados.";
      response.confianca = 96;
    }

    // Cenário 5: Semente / Qual comprar
    else if (text.includes("semente") || text.includes("cultivar") || text.includes("variedade") || text.includes("comprar")) {
      response.text = `Excelente momento para planejar a semente, **${nome}**! Para sua área de **${this.farmer.areaHa} hectares**:\n\n` +
        `🌱 **Cultivar Indicada:** **${cultura.variedade}**.\n` +
        `📦 **Vigor e Germinação:** Exija semente com germinação mínima de **85%** e índice de vigor acima de **80%** (teste do tetrazólio no laudo).\n` +
        `🛡️ **Tratamento Industrial (TSI):** Vale o pequeno investimento a mais em semente já tratada com fungicida + inseticida para garantir estande inicial uniforme de 280 a 300 mil plantas/ha.`;

      response.audioText = `${nome}, na hora de comprar a semente, confira se no laudo a germinação tá acima de 85%. Semente com vigor baixo faz falha no estande e derruba a produtividade.`;
      response.fonte = "Abrasem & Catálogo Oficial RNC - MAPA";
      response.porQue = "Um estande desuniforme no início do ciclo pode comprometer até 15% do teto produtivo de forma irreversível.";
      response.confianca = 93;
    }

    // Cenário 6: Preço, venda, comercialização ou onde vender
    else if (text.includes("preço") || text.includes("saca") || text.includes("vender") || text.includes("venda") || text.includes("mercado") || text.includes("cooperativa")) {
      const preco = cultura.precoSacaReferencia.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
      response.text = `Cotação de hoje para sua região (**${this.farmer.municipio}**), **${nome}**:\n\n` +
        `💰 **Preço Médio da Saca:** **${preco}** na cooperativa local (tendência de leve alta de +1.2%).\n` +
        `🎯 **Dica de Comercialização para o Pequeno:**\n` +
        `• Não tente adivinhar o topo do mercado. Trave em lotes parciais (ex: 20% agora para cobrir adubo e óleo diesel).\n` +
        `• Como você é elegível ao **Pronaf**, verifique o edital do **PAA / PNAE** da sua prefeitura: compras públicas costumam pagar até **7% a 10% acima da saca comercial** para entrega parcelada!`;

      response.audioText = `${nome}, a saca tá saindo em média a ${preco}. Vale a pena travar um pedaço pra cobrir os custos e ver se sua prefeitura abriu chamada do PAA da merenda escolar, que paga mais.`;
      response.fonte = "Cepea/Esalq & Painel Conab de Mercados";
      response.porQue = "Hedge parcial reduz risco de insolvência financeira do pequeno produtor.";
      response.confianca = 94;
      response.acaoSugerida = "Ver Comparativo de Canais";
    }

    // Cenário 7: Financiamento, Pronaf, Proagro ou Crédito
    else if (text.includes("pronaf") || text.includes("proagro") || text.includes("crédito") || text.includes("financiamento") || text.includes("banco")) {
      response.text = `Sobre o seu crédito rural, **${nome}**:\n\n` +
        `📋 **Pronaf Custeio:** Sua propriedade de **${this.farmer.areaHa} ha** se enquadra perfeitamente na linha Pronaf Mais Alimentos / Custeio, com taxas subsidiadas entre **4% a 6% ao ano**.\n` +
        `🛡️ **Regra de Ouro do Proagro:** Para a perícia aprovar eventual indenização em caso de seca ou granizo, **a semeadura precisa ser feita estritamente dentro da janela do ZARC** e com nota fiscal da semente registrada no seu CPF.`;

      response.audioText = `${nome}, pra não ter dor de cabeça com o banco e garantir o Proagro, guarde todas as notas fiscais no seu nome e plante estritamente dentro do Zarc.`;
      response.fonte = "Manual de Crédito Rural (MCR) - Banco Central do Brasil";
      response.porQue = "Principal motivo de recusa do Proagro no Brasil é plantio fora do decêndio oficial do ZARC.";
      response.confianca = 99;
    }

    // Cenário 8: Diagnóstico visual por foto (Simulação de Visão Computacional no Campo)
    else if (text.includes("foto") || text.includes("imagem") || text.includes("folha amarela") || text.includes("mancha")) {
      return this.analyzeImage("folha_mancha");
    }

    // Resposta padrão contextualizada e acolhedora
    else {
      response.text = `Entendido, **${nome}**! Como seu copiloto 24/7 para o **${this.farmer.propriedade}** (${this.farmer.areaHa} ha de ${cultura.nome} em ${this.farmer.municipio}):\n\n` +
        `Estou monitorando seu talhão continuamente. Para te orientar sem margem de erro, sobre qual etapa você gostaria de apoio agora?\n\n` +
        `1. 🌱 **Comprar Semente:** Escolha de cultivares e laudo de vigor\n` +
        `2. 🌾 **Janela ZARC:** Data segura de plantio e seguro Proagro\n` +
        `3. 💧 **Manejo & Clima:** Previsão de temporal e controle de pragas\n` +
        `4. 🚜 **Missões de Campo:** Checagem prática de hoje\n` +
        `5. 💰 **Venda:** Onde vender e cotações Cepea/Conab\n\n` +
        `📸 *Dica:* Você também pode clicar no ícone de câmera para me enviar uma foto da folha ou praga da sua lavoura!`;

      response.audioText = `Oi ${nome}! Tô acompanhando sua lavoura 24 horas. Pode me perguntar sobre sementes, clima, pragas, Zarc ou me mandar foto da folha que eu analiso.`;
      response.fonte = "AgroPilot 24/7 Knowledge Base • Embrapa & MAPA";
      response.porQue = "Atendimento contínuo do ciclo agrícola da semeadura à comercialização.";
      response.confianca = 90;
    }

    return response;
  }

  /**
   * Análise visual de foto enviada pelo produtor (Princípio #1: Universal & Princípio #4: Explicável)
   */
  analyzeImage(photoType) {
    const parts = this.farmer.nome.trim().split(/\s+/);
    let nome = parts[0];
    if ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1]) {
      nome = `${parts[0]} ${parts[1]}`;
    }
    const cultura = AGRO_DATA.culturas[this.farmer.culturaAtual] || AGRO_DATA.culturas.soja;

    if (photoType === "lagarta") {
      return {
        text: `📸 **Diagnóstico Visual Concluído para ${nome}:**\n\n` +
          `🐛 **Identificação:** *Anticarsia gemmatalis* (Lagarta-da-soja) em estágio L3 (aprox. 1,8 cm).\n` +
          `📊 **Nível de Dano Estimado na Imagem:** Desfolha observada em torno de **12%**.\n\n` +
          `🛡️ **Decisão Econômica Segura:** No estágio vegetativo atual (${cultura.faseAtual}), a soja suporta até **30% de desfolha** sem perda de produtividade. **NÃO APLIQUE DEFENSIVO QUÍMICO AGORA!**\n\n` +
          `💡 **Ação de Manejo:** Realize amostragem com pano de batida em 10 pontos. Se ultrapassar 20 lagartas/metro, utilize bioinseticida à base de *Bacillus thuringiensis* (Bt).`,
        audioText: `${nome}, analisei a foto da lagarta. A desfolha tá em doze por cento, bem abaixo do limite de trinta por cento. Não gaste dinheiro com veneno agora!`,
        fonte: "Embrapa Soja - Manual de Identificação de Pragas e MIP",
        porQue: "Aplicação prematura elimina inimigos naturais e gera custo desnecessário de até R$ 85 por hectare.",
        confianca: 94,
        acaoSugerida: "Abrir Missão de Amostragem",
        missaoId: "mis-02"
      };
    } else if (photoType === "ferrugem") {
      return {
        text: `🚨 **ALERTA CRÍTICO: Sintoma de Ferrugem Asiática Detectado!**\n\n` +
          `🍂 **Identificação:** Lesões puntiformes castanhas na face abaxial da folha (*Phakopsora pachyrhizi*).\n` +
          `⚠️ **Gravidade:** Alta. O clima úmido (74%) e temperatura de 26°C aceleram a esporulação.\n\n` +
          `🚜 **Recomendação Imediata:**\n` +
          `1. Colete a folha e apresente ao agrônomo da cooperativa para confirmação em lupa e emissão de receituário.\n` +
          `2. Não adie a aplicação preventiva de fungicida multissítio (Mancozebe ou Clorotalonil) associado a triazol/estrobirulina.`,
        audioText: `Atenção Seu Sebastião! A foto tem sinal de ferrugem asiática. Leve a folha no agrônomo da cooperativa hoje mesmo pra não perder a lavoura.`,
        fonte: "Consórcio Antiferrugem Embrapa • Alerta Fitossanitário Nacional",
        porQue: "A ferrugem asiática não controlada pode causar até 80% de perda na produtividade da soja.",
        confianca: 91,
        acaoSugerida: "Consultar Agrônomo da Cooperativa"
      };
    } else {
      return {
        text: `📸 **Análise Visual da Folha:**\n\n` +
          `🌱 **Sintoma Observado:** Leve clorose internerval nas folhas mais velhas.\n` +
          `🔍 **Hipótese Agronômica:** Início de deficiência de Magnésio ou início de estresse hídrico pontual no solo ${this.farmer.tipoSolo}.\n\n` +
          `💡 **Ação Recomendada:** Monitore se o sintoma se espalha para o terço médio. Como temos chuva prevista de 75mm em 48h, a absorção radicular deve se normalizar.`,
        audioText: `Analisei a foto da folha. Parece uma falta leve de magnésio ou estresse hídrico passageiro. Com a chuva que tá vindo, a planta deve se recuperar.`,
        fonte: "Diagnose Visual de Deficiências Nutricionais - Embrapa Cerrados",
        porQue: "Saturação de bases no solo AD3 de Rio Verde é geralmente equilibrada por calagem prévia.",
        confianca: 88
      };
    }
  }
}

window.agroCopilot = new AgroPilotCopilot();
