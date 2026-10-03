"""Roteador de intenção: classifica a mensagem por palavras-chave.

DESIGN (item 1.1 do backlog): antes, qualquer frase que não batesse em uma
keyword caía em NAO_ENTENDI e o LLM era chamado DEPOIS com o contexto
enviesado ("pergunta fora do escopo") — o próprio sistema fazia o modelo
responder "não entendi". Isso matava perguntas legítimas como
"quanto rende por hectare", "meu milho tá seco" ou "sou irrigado, mudo a data?".

Agora o vocabulário é largo e NAO_ENTENDI só sobra para o que é
realmente fora do escopo (programação, política, perguntas genéricas).
Mesmo assim o chamador ainda passa pelo LLM — nunca devolvemos
"não entendi" cru.
"""
import re

from ..schemas.intencoes import Intencao


# Palavras por intenção. Listas generosas de propósito: classificar errado
# é barato (o agente ainda chama as tools certas), mas classificar "não
# entendi" é caro — mata a conversa.
_KEYWORDS: dict[Intencao, tuple[str, ...]] = {
    Intencao.SAUDACAO: (
        r"\b(oi|ol[aá]|opa|e a[eé]|bom dia|boa tarde|boa noite|bom dia|sauda|"
        r"tudo bem|como (estou|e) |fal[aá]|e[ií] a[ií]|valeu|obrigado)\b",
    ),
    Intencao.PRAGA: (
        r"\b(m[ií]ldio|mildeo|oidio|o[ií]dio|lagarta|percevejo|pulg[aã]|pulga|broca|"
        r"mosca|cigarrinha|besouro|nemat|ferrugem|mancha|doen[cç]a|praga|pragas|"
        r"fungo|v[ií]rus|bichinho|bicho|inseto|infest|t[aã]o|queimad|necros|"
        r"encravamento|manchad|galho|planta (ta|t[aá]|est[aá])|"
        r"defensivo|agrot[oó]xico|veneno|remedio|rem[eé]dio|pesticida|"
        r"combatar|controle de praga|como combato)\b",
    ),
    Intencao.PLANEJAMENTO: (
        r"\b(plantar|plantio|planto|plantei|plantada|sement|semead|cultivar|"
        r"variedade|janela|zarc|adubar|"
        r"fertiliz|irrig|sequeiro|irrigado|ad1|ad2|ad3|dec[êe]n|portaria|"
        r"ciclo|[êé]poca do ano|melhor (m[eé]s|hora|epi[óo]rio)|"
        r"posso semear|recomend\w* .{0,12}sement|quanto rende|produtividade|"
        r"hectare|talh[aã]o|manejo|solo)\b",
    ),
    Intencao.CLIMA: (
        r"\b(geada|gear|frio|fria|chuva|chover|chuvas?|tempo|clima|"
        r"temperatur|calor|quente|seco|seca|veranico|enchente|"
        r"excesso de chuva|granizo|ventania|temporal|frente? fri|"
        r"umidade|orvalho|estacao|estação|sol forte|calor)\b",
    ),
    Intencao.VENDA: (
        r"\b(vender|venda|vendo|vendu|comercializ|entrega|negoci|feira|"
        r"pre[cç]o|pre[cç]os|cotac|cota[cç][aã]o|quanto vale|quanto recebo|"
        r"quanto pago|pagar por|mercado|cepea|conab|pgpm|paa|pnae|"
        r"cooperativa|cerealista|armaz[eé]m|canal de venda|onde vendo|"
        r"para quem vendo|quanto ta o kilo|saco|"
        r"colher|colheita|colho|colhendo|vender a colheita|destino da produ[cç][aã]o)\b",
    ),
    Intencao.PERFIL: (
        r"\b(meu perfil|minha terra|minha propriedade|minhas lavouras|"
        r"meu cadastro|meu nome|meu telefone|minha cidade|meu municipio|"
        r"meu mun[ií]cio|sobre mim|minha area|minha área|"
        r"meus dados|cadastro|conta|login|entrar na conta)\b",
    ),
}

_COMPILED = {k: re.compile(v[0]) for k, v in _KEYWORDS.items()}

# Coisas que NÃO são conversa de lavoura — aqui sim o "não entendi" faz sentido.
_FORA_DE_ESCOPO = re.compile(
    r"\b(python|javascript|java|script|algoritmo|codigo|c[óo]digo|"
    r"html|css|sql|regex|express[aã]o|compil|api do openai|"
    r"pol[ií]tica|presidente|elei[cç][aã]o|futebol|gol de|placar|campeonato|"
    r"filme|m[uú]sica|jogo do|quem ganhou|champions|liga |"
    r"escreva (um|uma) (poema|hist[óo]ria|letra|musica)|"
    r"traduz(a|e|ir)?\s+.{0,25}(ingl|ingles|ingl[eê]s|franc[eê]s|espanhol)|"
    r"traduza para o ingl|resolva (essa|esta) conta|derivada de)\b"
)


def fora_do_escopo(mensagem: str) -> bool:
    """True se a mensagem pede algo fora da agricultura (código, política...)."""
    return bool(_FORA_DE_ESCOPO.search((mensagem or "").lower()))


def classificar_intencao(mensagem: str) -> Intencao:
    """Classifica a intenção por palavras-chave (larga). Na dúvida, mantém SAUDACAO
    como neutro e deixa o agente/LM resolver — nunca devolve erro direto."""
    msg = (mensagem or "").lower().strip()
    if not msg:
        return Intencao.SAUDACAO

    # 1) fora do escopo tem prioridade máxima
    if _FORA_DE_ESCOPO.search(msg):
        return Intencao.NAO_ENTENDI

    # 2) "seco/queimando" com sujeito de lavoura é PRAGA, não clima.
    #    Precisa vir ANTES do loop: "meu milho tá seco" também casa em CLIMA.
    if re.search(
        r"\b(milho|soja|feij[aã]o|arroz|trigo|algod[ãa]o|cana|mandioca|batata|"
        r"tomate|caf[eé]|planta|lavoura|folha|mand[ií]bulo)\b.{0,25}\b(sec[oa]|"
        r"queim|amarel|murch|p[óo]dre)",
        msg,
    ):
        return Intencao.PRAGA

    # 3) intents específicas
    ordem = [
        Intencao.SAUDACAO,
        Intencao.PRAGA,
        Intencao.PLANEJAMENTO,
        Intencao.CLIMA,
        Intencao.VENDA,
        Intencao.PERFIL,
    ]
    for intent in ordem:
        if _COMPILED[intent].search(msg):
            return intent

    # 3) na dúvida: se parece pergunta de lavoura (curta, sem verbo neutro),
    #    manda pra PLANEJAMENTO (a intenção mais comum do produtor rural).
    #    O agente ainda decide pelas tools — só damos um ponto de partida.
    return Intencao.PLANEJAMENTO

