# =====================================================
# BATALHA v7
# Elementos e fraquezas, contratos, relíquias, ataques especiais com
# contador, ataques exclusivos de mega forma, dupla com 2 jogadores,
# bomba climática que depende do clima.
# =====================================================
import random
import unicodedata

# multiplicador
dado = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Para testar inimigos específicos, coloque os nomes aqui (deixe [] para sortear).
# Ex.: INIMIGOS_FORCADOS = ["gojo"]  ou  ["morcego", "ladrão"]
INIMIGOS_FORCADOS = []

# Chance (%) de o inimigo secreto aparecer no lugar de um inimigo sorteado.
CHANCE_SECRETO = 2

# =====================================================
# CONFIGURAÇÕES (ajuste o balanceamento aqui)
# =====================================================

# --- Efeitos de status ---------------------------------
# tipo "dano"   -> causa dano no início do turno e o personagem age normalmente
# tipo "impede" -> o personagem perde o turno
# tipo "lento" -> chance (%) de perder o turno e esquiva reduzida pela metade
# tipo "medo"   -> causa menos dano (multiplicador em "dano")
# "cura" (sangramento) -> multiplicador da cura recebida enquanto sangras
EFEITOS = {
    "veneno":      {"tipo": "dano",   "dano": 5, "estado": "envenenado"},
    "queima":      {"tipo": "dano",   "dano": 8, "estado": "queimado", "elemento": "fogo"},
    "sangramento": {"tipo": "dano",   "dano": 6, "estado": "sangrando", "cura": 0.5},
    "paralisado":  {"tipo": "impede", "estado": "paralisado"},
    "congelado":   {"tipo": "impede", "estado": "congelado"},
    "lento":       {"tipo": "lento",  "chance": 35, "estado": "lento"},
    "medo":        {"tipo": "medo",   "dano": 0.7, "estado": "com medo"},
    "aprisionado": {"tipo": "impede", "estado": "aprisionado"},
    "afundado":    {"tipo": "lento", "chance": 100, "estado": "afundado"},
    "vulneravel":  {"tipo": "vulneravel", "estado": "vulnerável"},
}

# --- Ressusitador (ativa sozinho quando um herói morre) -----
RESSUSCITADOR = {"chance": 50, "vida_percentual": 0.5, "imunidade": 2}

# --- Escudo dos heróis ------------------------------------
# Ao "defender", o escudo protege até o fim da próxima fase dos inimigos.
ESCUDO = {"absorcao": 0.7, "regeneracao": 5, "recarga": 3, "vida_ao_voltar": 0.5}

# --- Cura dos inimigos ------------------------------------
CURA_INIMIGO = {"energia": 30, "percentual_por_uso": 0.25, "limite_total": 0.5}

# --- Crítico e esquiva ------------------------------------
CRITICO = {"multiplicador": 1.5, "chance_padrao": 5}
# chance (%) de esquivar = velocidade / divisor (até "maximo") + bônus; nunca passa de "limite"
ESQUIVA = {"divisor": 5, "maximo": 30, "limite": 60}

# --- Recuperação de energia e descanso --------------------
REGEN_ENERGIA = 15
DESCANSO = {"energia": 30, "vida_pct": 0.05, "escudo": 10}

# --- Mega formas ------------------------------------------
FORMAS = {"duracao": 5, "energia_heroi": 40}

# --- Elementos, fraquezas, resistências e anulação --------
# Cada combatente tem um elemento (padrão "neutro"). Ele define as fraquezas,
# resistências e anulações automáticas (tabela abaixo). Também dá para escrever
# listas próprias no personagem: "fraquezas", "resistencias" e "anulacoes".
# fraco_a -> recebe mais dano desses elementos | resiste -> recebe menos | anula -> não recebe nada
ELEMENTOS = {
    "neutro": {},
    "fogo":   {"fraco_a": ["agua", "terra"],          "resiste": ["fogo", "planta", "gelo"]},
    "agua":   {"fraco_a": ["planta", "raio"],         "resiste": ["fogo", "agua", "gelo"]},
    "planta": {"fraco_a": ["fogo", "gelo"],           "resiste": ["agua", "terra", "planta", "raio"]},
    "gelo":   {"fraco_a": ["fogo", "terra"],          "resiste": ["gelo"]},
    "raio":   {"fraco_a": ["terra"],                  "resiste": ["raio"]},
    "terra":  {"fraco_a": ["agua", "planta", "gelo"], "resiste": ["fogo"], "anula": ["raio"]},
    "sombra": {"fraco_a": ["luz"],                    "resiste": ["sombra"]},
    "luz":    {"fraco_a": ["sombra"],                 "resiste": ["luz"]},
    "rocha":  {"fraco_a": ["agua", "planta", "terra"], "resiste": ["fogo", "neutro"], "anula": ["raio"]},
    "veneno": {"fraco_a": ["terra", "fantasma"], "resiste": ["planta", "veneno"]},
    "gas":    {"fraco_a": ["fogo", "ar"], "resiste": ["planta", "veneno"]},
    "metal":  {"fraco_a": ["fogo", "terra"], "resiste": ["planta", "neutro", "gelo"]},
    "fantasma": {"fraco_a": ["fantasma", "luz"], "resiste": ["neutro", "veneno"], "anula": ["neutro"]},
    "ar":     {"fraco_a": ["raio", "gelo"], "resiste": ["terra", "planta"]},
}
# Compatibilidade: o elemento antigo raio passa a ser chamado elétrico.
ELEMENTOS["eletrico"] = ELEMENTOS["raio"]
ELEMENTOS["terra"]["fraco_a"] = ["agua", "planta", "gelo"]
ELEMENTO_MULT = {"fraqueza": 1.5, "resistencia": 0.5}

# --- Clima ------------------------------------------------
# elementos -> multiplicador de dano por elemento
# esquiva_mult / esquiva_bonus -> alteram a esquiva de todos
# apaga -> efeitos removidos de todos no fim de cada rodada
# raio  -> dano de um raio que cai em um combatante aleatório no fim da rodada
# bomba -> o que a BOMBA CLIMÁTICA faz com esse clima (sem clima, só causa dano)
CLIMAS = {
    "limpo":      {"nome": "céu limpo", "descricao": "Sem efeitos.", "elementos": {},
                   "bomba": {"dano": 20}},
    "chuva":      {"nome": "chuva", "descricao": "Fogo -30%, água e raio +25%. Apaga a queimadura.",
                   "elementos": {"fogo": 0.7, "agua": 1.25, "raio": 1.25}, "apaga": ["queima"],
                   "bomba": {"dano": 25, "elemento": "agua", "efeito": "lento", "duracao": 2}},
    "sol":        {"nome": "sol forte", "descricao": "Fogo +30%, gelo -30%. Derrete o congelamento.",
                   "elementos": {"fogo": 1.3, "gelo": 0.7}, "apaga": ["congelado"],
                   "bomba": {"dano": 25, "elemento": "fogo", "efeito": "queima", "duracao": 3}},
    "neve":       {"nome": "neve", "descricao": "Gelo +30%, fogo -20%. Todos com metade da esquiva.",
                   "elementos": {"gelo": 1.3, "fogo": 0.8}, "esquiva_mult": 0.5,
                   "bomba": {"dano": 25, "elemento": "gelo", "efeito": "congelado", "duracao": 1}},
    "tempestade": {"nome": "tempestade", "descricao": "Raio +50%, fogo -30%. Um raio cai a cada rodada.",
                   "elementos": {"raio": 1.5, "fogo": 0.7}, "apaga": ["queima"], "raio": 12,
                   "bomba": {"dano": 35, "elemento": "raio", "efeito": "paralisado", "duracao": 1}},
    "neblina":    {"nome": "neblina", "descricao": "+10% de esquiva para todos.",
                   "elementos": {}, "esquiva_bonus": 10,
                   "bomba": {"dano": 20, "elemento": "sombra", "efeito": "medo", "duracao": 2}},
    "ventania":   {"nome": "ventania", "descricao": "Combatentes que não sejam do tipo ar ficam lentos.",
                   "elementos": {}, "bomba": {"dano": 20}},
    "chuva_trovoada": {"nome": "chuva com trovoada", "descricao": "Água e elétrico são fortalecidos.", "elementos": {"agua": 1.25, "raio": 1.25, "eletrico": 1.25}, "bomba": {"dano": 30, "elemento": "agua", "efeito": "paralisado", "duracao": 1}},
    "chuva_tempestade": {"nome": "chuva de tempestade", "descricao": "Água e ar são fortalecidos.", "elementos": {"agua": 1.25, "ar": 1.25}, "bomba": {"dano": 35, "elemento": "ar"}},
    "trovoada": {"nome": "trovoada", "descricao": "Fortalece ataques elétricos.", "elementos": {"raio": 1.25, "eletrico": 1.25}, "bomba": {"dano": 30, "elemento": "raio", "efeito": "paralisado", "duracao": 1}},
    "nevoa": {"nome": "névoa", "descricao": "A precisão de todos diminui bastante.", "elementos": {}, "esquiva_bonus": 35, "bomba": {"dano": 20}},
    "lua_sangue": {"nome": "lua de sangue", "descricao": "Clima sombrio que fortalece ataques de sombra e fogo.", "elementos": {"sombra": 1.2, "fogo": 1.2}, "bomba": {"dano": 30, "elemento": "sombra", "efeito": "medo", "duracao": 2}},
}
CLIMA_DURACAO = 5

# --- Dupla ------------------------------------------------
INVENTARIO_DUPLA = 2                       # multiplicador dos itens no modo dupla

# --- Relíquias dos inimigos -------------------------------
CHANCE_RELIQUIA_INIMIGO = 35               # % de chance de um inimigo sorteado carregar uma relíquia

# =====================================================
# ITENS (inventário compartilhado do grupo)
# =====================================================
# tipo "bomba"/"pedra": dano fixo (ignora defesa, mas respeita elemento) + efeito
# "area" atinge todos os inimigos. A bomba climática depende do clima (veja CLIMAS).
ITENS = {
    "poção de cura basica":      {"tipo": "cura", "cura": 20, "quantidade": 3},
    "poção de cura avançado":    {"tipo": "cura", "cura": 20, "quantidade": 2},
    "poção de cura hiper":       {"tipo": "cura", "cura": 60, "quantidade": 1},
    "poção de energia":          {"tipo": "energia", "energia": 40, "quantidade": 2},
    "antídoto":                  {"tipo": "antidoto", "quantidade": 2},
    "ressusitador":              {"tipo": "ressusitador", "quantidade": 1},
    "bomba de fumaça":           {"tipo": "fumaca", "quantidade": 1},
    "bomba de gelo":             {"tipo": "bomba", "dano": 10, "elemento": "gelo", "aplica": "congelado", "duracao": 1, "area": True, "quantidade": 1},
    "bomba de fogo":             {"tipo": "bomba", "dano": 20, "elemento": "fogo", "aplica": "queima", "duracao": 3, "area": True, "quantidade": 1},
    "bomba elétrica":            {"tipo": "bomba", "dano": 12, "elemento": "raio", "aplica": "paralisado", "duracao": 1, "area": True, "quantidade": 1},
    "bomba climática":           {"tipo": "climatica", "quantidade": 1},
    "pedra":                     {"tipo": "pedra", "dano": 5, "aplica": "paralisado", "duracao": 1, "chance": 40, "quantidade": 3},
    "poção de força":            {"tipo": "forca", "multiplicador": 1.25, "duracao": 3, "quantidade": 1},
    "poção de efeito aleatório": {"tipo": "aleatorio", "duracao": 3, "efeito_duracao": 2, "quantidade": 1},
    "poção de velocidade":       {"tipo": "velocidade", "velocidade": 25, "quantidade": 1},
    "elixir da negação": {"tipo": "negacao", "quantidade": 1},
    "bomba de água": {"tipo": "bomba", "dano": 8, "elemento": "agua", "aplica": "lento", "duracao": 2, "quantidade": 2},
    "bomba de gas": {"tipo": "bomba", "dano": 8, "elemento": "gas", "aplica": "lento", "duracao": 2, "quantidade": 2},
    "bomba de vinhas": {"tipo": "bomba", "dano": 5, "elemento": "planta", "aplica": "aprisionado", "duracao": 2, "quantidade": 2},
    "elixir da tipagem": {"tipo": "tipagem", "quantidade": 1},
    "poção maximadora": {"tipo": "maximizadora", "duracao": 3, "quantidade": 1},
    "bomba fragmentada": {"tipo": "bomba", "dano": 18, "area": True, "quantidade": 1},
    "cruz sagrada": {"tipo": "vulnerabilidade", "elementos": ["fantasma", "sombra"], "quantidade": 1},
    "correntes sombrias": {"tipo": "vulnerabilidade", "elementos": ["luz"], "quantidade": 1},
}

# =====================================================
# RELÍQUIAS (itens únicos equipados no começo da luta)
# =====================================================
# "vida_max" -> muda a vida máxima (0.05 = +5%, -0.25 = -25%)
# "mods"     -> mesmos modificadores das habilidades (dano, reducao, vampirismo, resist_status...)
RELIQUIAS = {
    "amuleto de vida":        {"descricao": "+5% de vida máxima.",
                               "vida_max": 0.05, "mods": {}},
    "armadura dourada":       {"descricao": "+100% de vida máxima e -10% de dano causado.",
                               "vida_max": 1.0, "mods": {"dano": 0.9}},
    "amuleto das almas":      {"descricao": "Recupera 20% do dano causado nos ataques.",
                               "vida_max": 0, "mods": {"vampirismo": 0.2}},
    "amuleto da resistência": {"descricao": "-25% de vida máxima e +80% de resistência a efeitos de status.",
                               "vida_max": -0.25, "mods": {"resist_status": 80}},
    "amuleto da força":       {"descricao": "+20% de dano e -20% de vida máxima.",
                               "vida_max": -0.2, "mods": {"dano": 1.2}},
}

RELIQUIAS_INIMIGO = {
    "coração sombrio":  {"descricao": "+15% de vida e recupera 10% do dano causado.",
                         "vida_max": 0.15, "mods": {"vampirismo": 0.10}},
    "armadura de ferro": {"descricao": "+25% de vida, +5 de defesa e -10% de dano.",
                          "vida_max": 0.25, "mods": {"defesa": 5, "dano": 0.9}},
    "colar de presas":  {"descricao": "+20% de dano e -10% de vida.",
                         "vida_max": -0.10, "mods": {"dano": 1.2}},
    "selo arcano":      {"descricao": "+5 de energia por turno e 40% de resistência a efeitos.",
                         "vida_max": 0, "mods": {"energia_turno": 5, "resist_status": 40}},
    "pele de dragão":   {"descricao": "Reduz 12% do dano recebido.",
                         "vida_max": 0, "mods": {"reducao": 0.12}},
}

RELIQUIAS.update({
    "espada elemental": {"descricao": "Altera o elemento dos ataques conforme o clima.", "vida_max": 0, "mods": {"espada_elemental": True}},
    "grande espada": {"descricao": "+50% de dano; ataques fortes precisam carregar.", "vida_max": 0, "mods": {"dano": 1.5}},
    "armadura amaldiçoada": {"descricao": "+100% de vida, -20% de dano e velocidade.", "vida_max": 1.0, "mods": {"dano": 0.8, "velocidade": -20}},
    "pingente da rejeição": {"descricao": "+100% vida, energia e velocidade; sem escudo, fuga, cura ou consumíveis arremessáveis.", "vida_max": 1.0, "mods": {"energia_max": 1.0, "velocidade_mult": 2.0}},
    "escudo heroico": {"descricao": "+100% de escudo; recebe +12,5% de dano.", "vida_max": 0, "mods": {"escudo_mult": 2.0, "reducao": -0.125}},
})
RELIQUIAS_INIMIGO.update({
    "katanas encantadas": {"descricao": "+20% contra combatentes armados com espada.", "vida_max": 0, "mods": {"dano_espadas": 1.2}},
    "amuleto da lua de sangue": {"descricao": "Invoca lua de sangue e aumenta atributos em 20%.", "vida_max": .2, "mods": {"dano": 1.2, "velocidade_mult": 1.2, "energia_max": .2, "escudo_mult": 1.2}},
    "amuleto infernal": {"descricao": "Invoca clima e terreno de fogo.", "vida_max": 0, "mods": {"terreno_infernal": True}},
    "óculos de velocista": {"descricao": "+20% de velocidade.", "vida_max": 0, "mods": {"velocidade_mult": 1.2}},
    "amuleto do roubo": {"descricao": "Permite roubar e usar itens do adversário.", "vida_max": 0, "mods": {"roubo": True}},
    "equipamento anti controle": {"descricao": "Anula cruz sagrada e correntes sombrias.", "vida_max": 0, "mods": {"anti_controle": True}},
})

# Novos efeitos de controle e vulnerabilidade usados pelos itens/terrenos.
EFEITOS.update({
    "aprisionado": {"tipo": "impede", "estado": "aprisionado"},
    "afundado": {"tipo": "lento", "chance": 100, "estado": "afundado"},
    "vulneravel": {"tipo": "vulneravel", "estado": "vulnerável"},
})

# =====================================================
# CONTRATOS (heróis e inimigos)
# =====================================================
# Dá um benefício, mas impõe uma restrição ("restringe": itens / defender / descansar).
# Quem faz um contrato NÃO pode usar mega forma, e quem usou mega forma NÃO pode fazer contrato.
# Para inimigos: "itens" = não pode curar.
CONTRATOS = {
    "contrato de sangue":  {"descricao": "Crítico garantido. Não pode usar itens (inimigo: não pode curar).",
                            "mods": {"critico": 100}, "restringe": ["itens"]},
    "contrato da fúria":   {"descricao": "+40% de dano. Não pode defender.",
                            "mods": {"dano": 1.4}, "restringe": ["defender"]},
    "contrato da sombra":  {"descricao": "+25% de esquiva e recupera 15% do dano causado. Não pode descansar.",
                            "mods": {"esquiva": 25, "vampirismo": 0.15}, "restringe": ["descansar"]},
    "contrato do tirano":  {"descricao": "-25% de dano recebido e +10% de dano. Não pode usar itens nem defender.",
                            "mods": {"reducao": 0.25, "dano": 1.1}, "restringe": ["itens", "defender"]},
}

# =====================================================
# ATAQUES
# =====================================================
# Campos opcionais:
#   "elemento"  -> elemento do ataque (fraquezas/resistências e clima)
#   "efeito"/"duracao"/"chance" -> efeito aplicado (chance em %, padrão 100)
#   "carrega"   -> turnos carregando antes de disparar (pode ser interrompido)
#   "requer"    -> ATAQUE ESPECIAL: só pode ser usado depois de N ataques (o contador zera ao usar)
#   "drena"     -> % do dano causado que volta como vida
#   "area"      -> atinge todos os alvos
#   "golpes"    -> quantidade de golpes (cada um com esquiva, dado e crítico próprios)
#   "util"      -> ataque sem dano: {"clima": nome} / {"protecao": valor, "rodadas": n} / {"cura": valor}
ATAQUES = {
    # ---- cavaleiro ----
    "espada":         {"dano": 10, "energia": 5},
    "corte":          {"dano": 15, "energia": 8},
    "corte duplos":   {"dano": 25, "energia": 15},
    "corte preciso":  {"dano": 35, "energia": 25},
    "corte perfeito": {"dano": 50, "energia": 60},
    "corte especial": {"dano": 75, "energia": 90, "carrega": 2, "requer": 5},
    # exclusivos das mega formas do cavaleiro
    "lâmina flamejante":   {"dano": 40, "energia": 20, "elemento": "fogo", "efeito": "queima", "duracao": 2},
    "onda cortante":       {"dano": 36, "energia": 20, "elemento": "agua", "efeito": "lento", "duracao": 2, "chance": 60},
    "chicote de espinhos": {"dano": 32, "energia": 18, "elemento": "planta", "efeito": "sangramento", "duracao": 2},

    # ---- mago (jogador) ----
    "raio arcano":        {"dano": 12, "energia": 8, "elemento": "raio"},
    "chama arcana":       {"dano": 32, "energia": 28, "elemento": "fogo", "efeito": "queima", "duracao": 2},
    "lança de gelo":      {"dano": 24, "energia": 25, "elemento": "gelo", "efeito": "congelado", "duracao": 1, "chance": 50},
    "descarga":           {"dano": 30, "energia": 35, "elemento": "raio", "efeito": "paralisado", "duracao": 1, "chance": 40},
    "barreira arcana":    {"dano": 0, "energia": 25, "util": {"protecao": 35, "rodadas": 3}},
    "invocar chuva":      {"dano": 0, "energia": 20, "util": {"clima": "chuva"}},
    "invocar tempestade": {"dano": 0, "energia": 35, "util": {"clima": "tempestade"}},
    "cura arcana":        {"dano": 0, "energia": 30, "util": {"cura": 25}},
    "supernova":          {"dano": 70, "energia": 60, "elemento": "fogo", "area": True, "requer": 4},
    # exclusivos das mega formas do mago
    "cometa arcano":      {"dano": 55, "energia": 40, "elemento": "luz", "requer": 3},
    "raio em cadeia":     {"dano": 28, "energia": 35, "elemento": "raio", "area": True},

    # ---- arqueiro (jogador) ----
    "flecha rápida":     {"dano": 12, "energia": 5},
    "flecha precisa":    {"dano": 22, "energia": 12},
    "flecha envenenada": {"dano": 14, "energia": 15, "elemento": "planta", "efeito": "veneno", "duracao": 2},
    "tiro carregado":    {"dano": 50, "energia": 35, "carrega": 1},
    "chuva de flechas":  {"dano": 18, "energia": 30, "area": True},
    "flecha de fumaça":  {"dano": 0, "energia": 20, "util": {"clima": "neblina"}},
    "flecha final":      {"dano": 90, "energia": 50, "requer": 5},
    # exclusivos das mega formas do arqueiro
    "tiro mortal":       {"dano": 70, "energia": 45, "requer": 3},
    "flechas sombrias":  {"dano": 9, "energia": 30, "golpes": 3, "elemento": "sombra", "efeito": "sangramento", "duracao": 2, "chance": 50},

    # ---- velocista (jogador) ----
    "soco rápido":    {"dano": 8, "energia": 4, "golpes": 2},
    "combo veloz":    {"dano": 6, "energia": 10, "golpes": 4},
    "corte sônico":   {"dano": 26, "energia": 15, "efeito": "sangramento", "duracao": 2, "chance": 50},
    "segundo fôlego": {"dano": 0, "energia": 20, "util": {"cura": 20}},
    "mil cortes":     {"dano": 7, "energia": 40, "golpes": 6, "requer": 5},
    # exclusivo da mega forma do velocista
    "trovão veloz":   {"dano": 10, "energia": 30, "golpes": 4, "elemento": "raio", "efeito": "paralisado", "duracao": 1, "chance": 25},

    # ---- morcego ----
    "morcego_mordida":  {"dano": 7, "energia": 2, "elemento": "sombra"},
    "mordida venenosa": {"dano": 4, "energia": 6, "elemento": "sombra", "efeito": "veneno", "duracao": 2},

    # ---- ladrão ----
    "batida_de_bastão": {"dano": 10, "energia": 5},
    "facada":           {"dano": 16, "energia": 10, "efeito": "sangramento", "duracao": 2, "chance": 50},

    # ---- lobo selvagem ----
    "mordida feroz":   {"dano": 12, "energia": 5, "efeito": "sangramento", "duracao": 2, "chance": 60},
    "uivo assustador": {"dano": 0, "energia": 15, "efeito": "medo", "duracao": 2, "area": True},

    # ---- slime venenoso ----
    "gosma":             {"dano": 10, "energia": 5, "elemento": "agua", "efeito": "veneno", "duracao": 2},
    "explosão de gosma": {"dano": 20, "energia": 25, "elemento": "agua", "efeito": "veneno", "duracao": 3, "area": True},

    # ---- esqueleto guerreiro ----
    "golpe de osso":      {"dano": 12, "energia": 5},
    "investida":          {"dano": 22, "energia": 15},
    "lâmina enferrujada": {"dano": 16, "energia": 10, "efeito": "veneno", "duracao": 2},

    # ---- goblin alquimista ----
    "frasco ácido":      {"dano": 12, "energia": 10, "elemento": "planta", "efeito": "veneno", "duracao": 2},
    "névoa pegajosa":    {"dano": 6, "energia": 15, "efeito": "lento", "duracao": 3},
    "explosão instável": {"dano": 30, "energia": 40, "elemento": "fogo", "efeito": "queima", "duracao": 2, "carrega": 1},
    "poção explosiva":   {"dano": 40, "energia": 35, "elemento": "fogo", "efeito": "queima", "duracao": 2},   # mega

    # ---- arqueiro bandido ----
    "flecha certeira": {"dano": 16, "energia": 8},

    # ---- fantasma ----
    "toque gélido": {"dano": 12, "energia": 10, "elemento": "gelo", "efeito": "medo", "duracao": 2},
    "assombrar":    {"dano": 0, "energia": 20, "elemento": "sombra", "efeito": "medo", "duracao": 3, "area": True},
    "possessão":    {"dano": 25, "energia": 40, "elemento": "sombra", "efeito": "paralisado", "duracao": 1},

    # ---- espadashim arrogante ----
    "espadada":          {"dano": 15, "energia": 5},
    "slash":             {"dano": 20, "energia": 10},
    "true double slash": {"dano": 35, "energia": 45, "carrega": 1, "requer": 3},
    "kunai":             {"dano": 10, "energia": 5, "efeito": "sangramento", "duracao": 2, "chance": 40},
    "golpe furioso":     {"dano": 45, "energia": 40, "requer": 3},                                  # mega X
    "tempestade de kunais": {"dano": 8, "energia": 30, "golpes": 4, "efeito": "sangramento", "duracao": 2, "chance": 40},  # mega Y

    # ---- golem de gelo ----
    "punho gélido": {"dano": 18, "energia": 15, "elemento": "gelo", "efeito": "congelado", "duracao": 1},
    "avalanche":    {"dano": 40, "energia": 45, "elemento": "gelo", "carrega": 1, "area": True, "requer": 3},
    "terremoto glacial": {"dano": 35, "energia": 40, "elemento": "terra", "area": True},           # mega

    # ---- necromante ----
    "toque sombrio":     {"dano": 15, "energia": 15, "elemento": "sombra", "efeito": "veneno", "duracao": 3},
    "drenar vida":       {"dano": 20, "energia": 30, "elemento": "sombra", "drena": 0.5},
    "explosão de almas": {"dano": 45, "energia": 60, "elemento": "sombra", "carrega": 1, "requer": 3},
    "ceifar almas":      {"dano": 40, "energia": 50, "elemento": "sombra", "drena": 0.6},           # mega

    # ---- mestre mago ----
    "venom shot":           {"dano": 20, "energia": 25, "efeito": "veneno", "duracao": 3},
    "iceberg":              {"dano": 15, "energia": 25, "elemento": "gelo", "efeito": "congelado", "duracao": 1},
    "triplo bola elétrica": {"dano": 30, "energia": 50, "elemento": "raio", "efeito": "paralisado", "duracao": 1},
    "bola de fogo":         {"dano": 55, "energia": 60, "elemento": "fogo", "efeito": "queima", "duracao": 3, "carrega": 1},
    "the last blast":       {"dano": 75, "energia": 80, "carrega": 2, "requer": 4},
    "meteoro":              {"dano": 60, "energia": 70, "elemento": "fogo", "area": True, "carrega": 1},   # mega X
    "relâmpago supremo":    {"dano": 70, "energia": 70, "elemento": "raio"},                         # mega Y

    # ---- O supremo velocista ----
    "socos rapidos": {"dano": 7, "energia": 10, "golpes": 2},
    "paralização":   {"dano": 6, "energia": 20, "efeito": "paralisado", "duracao": 1},
    "faquinha":      {"dano": 18, "energia": 12, "efeito": "sangramento", "duracao": 2, "chance": 40},
    "HAHAHAHAHA a loucura de um velocista": {"dano": 8, "energia": 15, "efeito": "lento", "duracao": 2},
    "fractal":       {"dano": 10, "energia": 5},
    "velocidade da luz": {"dano": 6, "energia": 50, "golpes": 6, "elemento": "raio", "requer": 3},  # mega

    # ---- dragão jovem ----
    "garras":           {"dano": 20, "energia": 10, "efeito": "sangramento", "duracao": 2, "chance": 60},
    "baforada de fogo": {"dano": 38, "energia": 40, "elemento": "fogo", "efeito": "queima", "duracao": 3, "area": True},
    "rugido":           {"dano": 0, "energia": 25, "efeito": "medo", "duracao": 3, "area": True},
    "chama ancestral":  {"dano": 75, "energia": 85, "elemento": "fogo", "carrega": 2, "area": True, "requer": 4},
    "céu em chamas":    {"dano": 0, "energia": 25, "util": {"clima": "sol"}},
    "inferno":          {"dano": 70, "energia": 60, "elemento": "fogo", "area": True},              # mega

    # ---- gojo (secreto) ----
    "azul":     {"dano": 25, "energia": 20, "elemento": "luz", "efeito": "lento", "duracao": 2},
    "vermelho": {"dano": 45, "energia": 40, "elemento": "luz", "efeito": "sangramento", "duracao": 3},
    "roxo":     {"dano": 100, "energia": 100, "elemento": "luz", "carrega": 2, "requer": 4},
    "barreira": {"dano": 0, "energia": 40, "util": {"protecao": 70, "rodadas": 3}},
    "vazio imaginário": {"dano": 70, "energia": 60, "elemento": "luz", "area": True},               # mega
}

# =====================================================
# HABILIDADES E MEGA FORMAS
# =====================================================
# Modificadores ("mods") usados nas habilidades, bônus de forma, relíquias e contratos:
#   dano (multiplica), reducao (% de dano recebido reduzido), defesa (+), critico (+%), esquiva (+%),
#   energia_turno (+), vida_turno (+), vampirismo (% do dano vira vida), espinhos (% do dano recebido
#   volta), perfura (% da defesa do alvo ignorada), resist_status (% de resistir a um efeito),
#   furia {"vida_pct","dano"}, contra {"chance","dano"}, on_hit {"efeito","duracao","chance"}
#
# Mega forma: "bonus" (mods) + "habilidade" (habilidade especial da forma) +
#   "ataques" (ataques EXCLUSIVOS enquanto a forma durar) + "elemento" (muda o elemento do
#   personagem e dos ataques sem elemento) +
#   "por_turno" ({"aplica": {...}} nos inimigos ou {"cura": n}) +
#   "ao_transformar" ({"cura": %, "energia_cheia": True, "clima": nome, "aplica": {...}})
# A letra (X, Y, Z) só existe quando o personagem tem mais de uma ramificação de mega.

# =====================================================
# CLASSES JOGÁVEIS
# =====================================================
CLASSES = {
    "cavaleiro": {
        "vida": 100, "energia": 100, "velocidade": 20, "critico": 10, "defesa": 0, "escudo": 50,
        "ataques": ["espada", "corte", "corte duplos", "corte preciso", "corte perfeito", "corte especial"],
        "habilidade": {"nome": "Bravura", "descricao": "Com 30% de vida ou menos, causa 20% mais dano.",
                       "mods": {"furia": {"vida_pct": 30, "dano": 1.2}}},
        "formas": [
            {"letra": "X", "nome": "Mega Fogo", "elemento": "fogo", "descricao": "Queima o inimigo a cada turno.",
             "por_turno": {"aplica": {"efeito": "queima", "duracao": 2}},
             "ataques": ["lâmina flamejante"],
             "habilidade": {"nome": "Aura Ígnea", "descricao": "Reflete 15% do dano recebido.", "mods": {"espinhos": 0.15}}},
            {"letra": "Y", "nome": "Mega Água", "elemento": "agua", "descricao": "Deixa o inimigo lento a cada turno.",
             "por_turno": {"aplica": {"efeito": "lento", "duracao": 2}},
             "ataques": ["onda cortante"],
             "habilidade": {"nome": "Maré Viva", "descricao": "+15% de esquiva.", "mods": {"esquiva": 15}}},
            {"letra": "Z", "nome": "Mega Planta", "elemento": "planta", "descricao": "Regenera 8 de vida por turno.",
             "por_turno": {"cura": 8},
             "ataques": ["chicote de espinhos"],
             "habilidade": {"nome": "Raízes", "descricao": "Reduz 10% do dano recebido.", "mods": {"reducao": 0.10}}},
        ],
    },
    "mago": {
        "vida": 80, "energia": 120, "velocidade": 60, "critico": 5, "defesa": 0, "escudo": 30,
        "ataques": ["raio arcano", "chama arcana", "lança de gelo", "descarga",
                    "barreira arcana", "invocar chuva", "cura arcana", "supernova"],
        "habilidade": {"nome": "Canalizar", "descricao": "+5 de energia por turno.",
                       "mods": {"energia_turno": 5}},
        "formas": [
            {"letra": "X", "nome": "Arquimago", "descricao": "Dano +15% e +20 de energia por turno.",
             "bonus": {"dano": 1.15, "energia_turno": 20},
             "ataques": ["cometa arcano"],
             "habilidade": {"nome": "Sobrecarga", "descricao": "+15% de crítico.", "mods": {"critico": 15}}},
            {"letra": "Y", "nome": "Sábio das Tempestades", "descricao": "Chama uma tempestade ao se transformar.",
             "ao_transformar": {"clima": "tempestade"},
             "ataques": ["raio em cadeia"],
             "habilidade": {"nome": "Olho da Tempestade", "descricao": "Reduz 15% do dano recebido.", "mods": {"reducao": 0.15}}},
        ],
    },
    "arqueiro": {
        "vida": 90, "energia": 100, "velocidade": 70, "critico": 25, "defesa": 0, "escudo": 40,
        "ataques": ["flecha rápida", "flecha precisa", "flecha envenenada",
                    "tiro carregado", "chuva de flechas", "flecha de fumaça", "flecha final"],
        "habilidade": {"nome": "Perfurante", "descricao": "Ignora 25% da defesa do alvo.",
                       "mods": {"perfura": 0.25}},
        "formas": [
            {"letra": "X", "nome": "Olho de Águia", "descricao": "+25% de crítico e dano +15%.",
             "bonus": {"critico": 25, "dano": 1.15},
             "ataques": ["tiro mortal"],
             "habilidade": {"nome": "Tiro Certeiro", "descricao": "Ignora mais 25% da defesa.", "mods": {"perfura": 0.25}}},
            {"letra": "Y", "nome": "Caçador Sombrio", "elemento": "sombra", "descricao": "+20% de esquiva.",
             "bonus": {"esquiva": 20},
             "ataques": ["flechas sombrias"],
             "habilidade": {"nome": "Sangria", "descricao": "50% de chance de causar sangramento ao acertar.",
                            "mods": {"on_hit": {"efeito": "sangramento", "duracao": 2, "chance": 50}}}},
        ],
    },
    "velocista": {
        "vida": 75, "energia": 90, "velocidade": 200, "critico": 15, "defesa": 0, "escudo": 30,
        "ataques": ["soco rápido", "combo veloz", "corte sônico", "segundo fôlego", "mil cortes"],
        "habilidade": {"nome": "Ímpeto", "descricao": "+5 de energia por turno e +5% de esquiva.",
                       "mods": {"energia_turno": 5, "esquiva": 5}},
        "formas": [
            {"letra": None, "nome": "Modo Relâmpago", "elemento": "raio", "descricao": "Dano +20% e +15% de esquiva.",
             "bonus": {"dano": 1.2, "esquiva": 15},
             "ataques": ["trovão veloz"],
             "habilidade": {"nome": "Rastro Elétrico", "descricao": "25% de chance de paralisar ao acertar.",
                            "mods": {"on_hit": {"efeito": "paralisado", "duracao": 1, "chance": 25}}}},
        ],
    },
}

# =====================================================
# INIMIGOS
# =====================================================
# "elemento"     -> elemento do inimigo (define fraquezas/resistências/anulações pela tabela)
# "fraquezas", "resistencias", "anulacoes" -> listas próprias (somam à tabela do elemento)
# "contratos"    -> contratos que ele pode fazer (se fizer, não pode se transformar, e vice-versa)
# "acoes": atacar, defender, curar, transformar, contrato, fugir (descansar é automático)
# "forma_vida_pct": só se transforma com a vida abaixo desse valor (%)
INIMIGOS = {
    # ------------------------- FÁCIL -------------------------
    "morcego": {
        "artigo": "o", "elemento": "sombra",
        "vida": 20, "defesa": 5, "velocidade": 40, "energia": 20, "critico": 5,
        "ataques": ["morcego_mordida", "mordida venenosa"],
        "acoes": ["atacar", "fugir"],
        "habilidade": {"nome": "Sonar", "descricao": "+10% de esquiva.", "mods": {"esquiva": 10}},
    },
    "ladrão": {
        "artigo": "o", "elemento": "neutro",
        "vida": 65, "defesa": 22, "velocidade": 70, "energia": 45, "critico": 20,
        "ataques": ["batida_de_bastão", "facada"],
        "acoes": ["atacar", "defender", "contrato", "fugir"],
        "contratos": ["contrato de sangue"],
        "habilidade": {"nome": "Furtivo", "descricao": "+5% de esquiva.", "mods": {"esquiva": 5}},
    },
    "lobo selvagem": {
        "artigo": "o", "elemento": "neutro",
        "vida": 45, "defesa": 8, "velocidade": 90, "energia": 40, "critico": 10,
        "ataques": ["mordida feroz", "uivo assustador"],
        "acoes": ["atacar", "fugir"],
        "habilidade": {"nome": "Faro de Sangue", "descricao": "Com 50% de vida ou menos, causa 25% mais dano.",
                       "mods": {"furia": {"vida_pct": 50, "dano": 1.25}}},
    },
    "slime venenoso": {
        "artigo": "o", "elemento": "agua",
        "vida": 55, "defesa": 5, "velocidade": 10, "energia": 40, "critico": 0,
        "ataques": ["gosma", "explosão de gosma"],
        "acoes": ["atacar", "defender"],
        "habilidade": {"nome": "Corpo Gelatinoso", "descricao": "Reduz 15% do dano recebido.",
                       "mods": {"reducao": 0.15}},
    },

    # ------------------------- MÉDIO -------------------------
    "esqueleto guerreiro": {
        "artigo": "o", "elemento": "sombra",
        "vida": 70, "defesa": 25, "velocidade": 25, "energia": 60, "critico": 5,
        "ataques": ["golpe de osso", "investida", "lâmina enferrujada"],
        "acoes": ["atacar", "defender", "contrato", "fugir"],
        "contratos": ["contrato da fúria"],
        "habilidade": {"nome": "Ossos Duros", "descricao": "Reduz 10% do dano recebido.",
                       "mods": {"reducao": 0.10}},
    },
    "goblin alquimista": {
        "artigo": "o", "elemento": "planta",
        "vida": 60, "defesa": 10, "velocidade": 80, "energia": 70, "critico": 10,
        "ataques": ["frasco ácido", "névoa pegajosa", "explosão instável"],
        "acoes": ["atacar", "defender", "curar", "transformar", "fugir"],
        "habilidade": {"nome": "Poeira Pegajosa", "descricao": "20% de chance de deixar o alvo lento ao acertar.",
                       "mods": {"on_hit": {"efeito": "lento", "duracao": 1, "chance": 20}}},
        "forma_vida_pct": 50,
        "formas": [
            {"letra": None, "nome": "Goblin Mutante", "descricao": "Dano +30% e +10 de energia por turno.",
             "bonus": {"dano": 1.3, "energia_turno": 10},
             "ataques": ["poção explosiva"],
             "habilidade": {"nome": "Mutação Instável", "descricao": "Recupera 15% do dano causado.",
                            "mods": {"vampirismo": 0.15}}},
        ],
    },
    "arqueiro bandido": {
        "artigo": "o", "elemento": "planta",
        "vida": 65, "defesa": 12, "velocidade": 100, "energia": 60, "critico": 20,
        "ataques": ["flecha certeira", "flecha envenenada", "chuva de flechas"],
        "acoes": ["atacar", "defender", "fugir"],
        "habilidade": {"nome": "Mira Afiada", "descricao": "Ignora 25% da defesa do alvo.",
                       "mods": {"perfura": 0.25}},
    },
    "fantasma": {
        "artigo": "o", "elemento": "sombra", "resistencias": ["neutro"],
        "vida": 60, "defesa": 5, "velocidade": 120, "energia": 80, "critico": 5,
        "ataques": ["toque gélido", "assombrar", "possessão"],
        "acoes": ["atacar", "contrato", "fugir"],
        "contratos": ["contrato da sombra"],
        "habilidade": {"nome": "Incorpóreo", "descricao": "+15% de esquiva e resiste a ataques sem elemento.",
                       "mods": {"esquiva": 15}},
    },

    # ------------------------- DIFÍCIL -------------------------
    "espadashim arrogante": {
        "artigo": "o", "elemento": "terra",
        "vida": 85, "defesa": 32, "velocidade": 30, "energia": 100, "critico": 10,
        "ataques": ["espadada", "slash", "true double slash", "kunai"],
        "acoes": ["atacar", "defender", "curar", "transformar", "fugir"],
        "habilidade": {"nome": "Postura de Duelista", "descricao": "20% de chance de contra-atacar (10 de dano).",
                       "mods": {"contra": {"chance": 20, "dano": 10}}},
        "forma_vida_pct": 50,
        "formas": [
            {"letra": "X", "nome": "Espadashim Furioso", "descricao": "Dano +25%.",
             "bonus": {"dano": 1.25},
             "ataques": ["golpe furioso"],
             "habilidade": {"nome": "Fúria Cega", "descricao": "Recupera 10% do dano causado.",
                            "mods": {"vampirismo": 0.10}}},
            {"letra": "Y", "nome": "Espadashim Kunai", "descricao": "+20% de esquiva.",
             "bonus": {"esquiva": 20},
             "ataques": ["tempestade de kunais"],
             "habilidade": {"nome": "Chuva de Kunais", "descricao": "40% de chance de causar sangramento ao acertar.",
                            "mods": {"on_hit": {"efeito": "sangramento", "duracao": 2, "chance": 40}}}},
        ],
    },
    "golem de gelo": {
        "artigo": "o", "elemento": "gelo",
        "vida": 120, "defesa": 38, "velocidade": 5, "energia": 60, "critico": 0,
        "ataques": ["punho gélido", "avalanche"],
        "acoes": ["atacar", "defender", "transformar"],
        "habilidade": {"nome": "Corpo de Gelo", "descricao": "Reduz 10% do dano recebido.",
                       "mods": {"reducao": 0.10}},
        "forma_vida_pct": 60,
        "formas": [
            {"letra": None, "nome": "Cascata Glacial", "descricao": "Defesa +15.",
             "bonus": {"defesa": 15},
             "ataques": ["terremoto glacial"],
             "habilidade": {"nome": "Espinhos de Gelo", "descricao": "Reflete 20% do dano recebido.",
                            "mods": {"espinhos": 0.20}}},
        ],
    },
    "necromante": {
        "artigo": "o", "elemento": "sombra",
        "vida": 120, "defesa": 20, "velocidade": 60, "energia": 100, "critico": 8,
        "ataques": ["toque sombrio", "drenar vida", "explosão de almas"],
        "acoes": ["atacar", "defender", "curar", "transformar", "contrato", "fugir"],
        "contratos": ["contrato do tirano"],
        "habilidade": {"nome": "Sede de Almas", "descricao": "Recupera 10% do dano causado.",
                       "mods": {"vampirismo": 0.10}},
        "forma_vida_pct": 50,
        "formas": [
            {"letra": None, "nome": "Lich Supremo", "descricao": "Dano +10% e cura 20% da vida ao se transformar.",
             "bonus": {"dano": 1.1},
             "ao_transformar": {"cura": 0.2},
             "ataques": ["ceifar almas"],
             "habilidade": {"nome": "Aura Sombria", "descricao": "30% de chance de causar medo ao acertar.",
                            "mods": {"on_hit": {"efeito": "medo", "duracao": 2, "chance": 30}}}},
        ],
    },

    # ------------------------- CHEFES -------------------------
    "mestre mago": {
        "artigo": "o", "elemento": "neutro",
        "vida": 130, "defesa": 12, "velocidade": 150, "energia": 100, "critico": 5,
        "ataques": ["raio arcano", "venom shot", "iceberg", "triplo bola elétrica", "bola de fogo",
                    "the last blast", "barreira arcana", "invocar chuva", "invocar tempestade"],
        "acoes": ["atacar", "defender", "curar", "transformar", "fugir"],
        "habilidade": {"nome": "Mestre dos Elementos", "descricao": "+5 de energia por turno.",
                       "mods": {"energia_turno": 5}},
        "forma_vida_pct": 60,
        "formas": [
            {"letra": "X", "nome": "Mestre Arcano Ascendido", "descricao": "Dano +15% e +25 de energia por turno.",
             "bonus": {"dano": 1.15, "energia_turno": 25},
             "ataques": ["meteoro"],
             "habilidade": {"nome": "Sobrecarga", "descricao": "+15% de crítico.", "mods": {"critico": 15}}},
            {"letra": "Y", "nome": "Oráculo da Tempestade", "descricao": "Chama uma tempestade ao se transformar.",
             "ao_transformar": {"clima": "tempestade"},
             "ataques": ["relâmpago supremo"],
             "habilidade": {"nome": "Olho da Tempestade", "descricao": "Reduz 15% do dano recebido.",
                            "mods": {"reducao": 0.15}}},
        ],
    },
    "supremo velocista": {
        "artigo": "o", "elemento": "raio",
        "vida": 110, "defesa": 18, "velocidade": 1000, "energia": 100, "critico": 15,
        "ataques": ["socos rapidos", "paralização", "faquinha", "HAHAHAHAHA a loucura de um velocista", "fractal"],
        "acoes": ["atacar", "defender", "curar", "transformar", "contrato", "fugir"],
        "contratos": ["contrato da sombra"],
        "habilidade": {"nome": "Supervelocidade", "descricao": "+5 de energia por turno.",
                       "mods": {"energia_turno": 5}},
        "forma_vida_pct": 50,
        "formas": [
            {"letra": None, "nome": "Avatar da Tempestade", "descricao": "Dano +20% e +15% de esquiva.",
             "bonus": {"dano": 1.2, "esquiva": 15},
             "ataques": ["velocidade da luz"],
             "habilidade": {"nome": "Rastro Elétrico", "descricao": "25% de chance de paralisar ao acertar.",
                            "mods": {"on_hit": {"efeito": "paralisado", "duracao": 1, "chance": 25}}}},
        ],
    },
    "dragão jovem": {
        "artigo": "o", "elemento": "fogo",
        "vida": 170, "defesa": 30, "velocidade": 50, "energia": 100, "critico": 5,
        "ataques": ["garras", "baforada de fogo", "rugido", "chama ancestral", "céu em chamas"],
        "acoes": ["atacar", "defender", "curar", "transformar", "contrato", "fugir"],
        "contratos": ["contrato da fúria"],
        "habilidade": {"nome": "Escamas", "descricao": "Reduz 15% do dano recebido.",
                       "mods": {"reducao": 0.15}},
        "forma_vida_pct": 50,
        "formas": [
            {"letra": None, "nome": "Dragão Furioso", "descricao": "Dano +20%, defesa +10 e chama o sol forte.",
             "bonus": {"dano": 1.2, "defesa": 10},
             "ao_transformar": {"clima": "sol"},
             "ataques": ["inferno"],
             "habilidade": {"nome": "Fogo Infernal", "descricao": "Reflete 10% do dano recebido.",
                            "mods": {"espinhos": 0.10}}},
        ],
    },

    # ------------------------- SECRETO -------------------------
    "gojo": {
        "artigo": "", "elemento": "luz",
        "vida": 200, "defesa": 25, "velocidade": 300, "energia": 150, "critico": 10,
        "ataques": ["azul", "vermelho", "roxo", "barreira"],
        "acoes": ["atacar", "curar", "transformar", "contrato"],
        "contratos": ["contrato da fúria"],
        "habilidade": {"nome": "Infinito", "descricao": "Reduz 30% do dano recebido e +15% de esquiva.",
                       "mods": {"reducao": 0.30, "esquiva": 15}},
        "forma_vida_pct": 60,
        "formas": [
            {"letra": None, "nome": "Vazio Ilimitado", "descricao": "Dano +25%, energia cheia e paralisa todos por 1 turno.",
             "bonus": {"dano": 1.25},
             "ao_transformar": {"energia_cheia": True, "aplica": {"efeito": "paralisado", "duracao": 1}},
             "ataques": ["vazio imaginário"],
             "habilidade": {"nome": "Domínio Absoluto", "descricao": "+20% de crítico.", "mods": {"critico": 20}}},
        ],
    },
}

# Expansão do patch: conteúdo partilhado pela versão de terminal e Pygame.
ATAQUES.update({
    "disparo preciso": {"dano": 24, "energia": 15, "elemento": "neutro"},
    "tiro carregado": {"dano": 52, "energia": 35, "carrega": 2},
    "tiro de prata": {"dano": 32, "energia": 25, "elemento": "metal"},
    "soco de boxe": {"dano": 18, "energia": 10, "golpes": 2},
    "gancho": {"dano": 34, "energia": 24, "efeito": "lento", "duracao": 1},
    "punho do monge": {"dano": 22, "energia": 16, "elemento": "neutro"},
    "onda interior": {"dano": 38, "energia": 32, "elemento": "ar", "area": True},
    "corte sombrio": {"dano": 28, "energia": 20, "elemento": "sombra", "efeito": "medo", "duracao": 2},
    "poção corrosiva": {"dano": 24, "energia": 20, "elemento": "veneno", "efeito": "veneno", "duracao": 3},
    "escudo pesado": {"dano": 0, "energia": 22, "util": {"protecao": 45, "rodadas": 2}},
    "deslizamento de pedra": {"dano": 28, "energia": 18, "elemento": "rocha"},
    "soco de pedra": {"dano": 22, "energia": 12, "elemento": "rocha"},
    "rolamento": {"dano": 25, "energia": 16, "elemento": "rocha", "efeito": "lento", "duracao": 1},
    "esmagar": {"dano": 45, "energia": 35, "elemento": "rocha", "carrega": 1},
    "espinhos venenosos": {"dano": 22, "energia": 20, "elemento": "veneno", "efeito": "veneno", "duracao": 3, "area": True},
    "metal cannon": {"dano": 35, "energia": 25, "elemento": "metal"},
    "martelo metálico": {"dano": 32, "energia": 20, "elemento": "metal"},
    "estouro metálico": {"dano": 42, "energia": 35, "elemento": "metal", "area": True},
    "soco de metal": {"dano": 25, "energia": 14, "elemento": "metal"},
    "canhão vulcânico": {"dano": 62, "energia": 48, "elemento": "fogo", "efeito": "queima", "duracao": 2},
    "tiro prateado": {"dano": 28, "energia": 18, "elemento": "metal"},
    "headshot": {"dano": 60, "energia": 45, "carrega": 1},
    "seis disparos": {"dano": 12, "energia": 30, "golpes": 6},
    "avanço conquistador": {"dano": 24, "energia": 14},
    "batida pesada": {"dano": 40, "energia": 28, "elemento": "metal"},
    "trovoada conquistadora": {"dano": 44, "energia": 32, "elemento": "ar"},
    "vento conquistador": {"dano": 66, "energia": 50, "elemento": "ar", "area": True},
    "martelada": {"dano": 20, "energia": 10},
    "culpado": {"dano": 28, "energia": 20, "elemento": "luz"},
    "suspeito": {"dano": 14, "energia": 12, "efeito": "medo", "duracao": 1},
    "inocentado": {"dano": 0, "energia": 18, "util": {"cura": 25}},
    "ataque de luz": {"dano": 32, "energia": 24, "elemento": "luz"},
    "execução final": {"dano": 75, "energia": 60, "elemento": "luz", "carrega": 1},
    "jato venenoso": {"dano": 38, "energia": 26, "elemento": "veneno", "efeito": "veneno", "duracao": 3},
    "mordida venenosa": {"dano": 28, "energia": 18, "elemento": "veneno", "efeito": "veneno", "duracao": 2},
    "olhar medonho": {"dano": 0, "energia": 25, "efeito": "medo", "duracao": 2, "area": True},
    "veneno final": {"dano": 72, "energia": 55, "elemento": "veneno", "efeito": "veneno", "duracao": 4},
    "corte duplo": {"dano": 19, "energia": 12, "golpes": 2},
    "corte X": {"dano": 35, "energia": 25, "golpes": 2},
    "último slash": {"dano": 70, "energia": 55, "elemento": "metal"},
    "batida": {"dano": 20, "energia": 12},
    "intimidar": {"dano": 0, "energia": 20, "efeito": "medo", "duracao": 2, "area": True},
})

CLASSES.update({
    "atirador": {"vida": 85, "energia": 120, "velocidade": 45, "critico": 18, "defesa": 0, "escudo": 35,
        "elemento": "neutro", "ataques": ["disparo preciso", "tiro carregado", "tiro de prata", "flecha final"],
        "habilidade": {"nome": "Mira paciente", "descricao": "Ataques carregados causam alto dano.", "mods": {"dano": 1.1}},
        "formas": [{"letra": "X", "nome": "Atirador de elite",
                    "descricao": "Mira absoluta: aumenta dano e crítico e libera Headshot.",
                    "bonus": {"dano": 1.2, "critico": 15},
                    "ataques": ["headshot"]}]},
    "boxeador": {"vida": 115, "energia": 90, "velocidade": 65, "critico": 12, "defesa": 5, "escudo": 45,
        "ataques": ["soco de boxe", "gancho", "combo veloz", "corte sônico"],
        "habilidade": {"nome": "Guarda fechada", "descricao": "Resiste ao controle.", "mods": {"resist_status": 20}},
        "formas": [{"nome": "Punho do Titã", "descricao": "Golpes mais fortes e defesa reforçada.",
                    "bonus": {"dano": 1.25, "reducao": 0.15}, "ataques": ["gancho", "combo veloz"]}]},
    "monge": {"vida": 100, "energia": 110, "velocidade": 75, "critico": 15, "defesa": 5, "escudo": 35,
        "elemento": "ar", "ataques": ["punho do monge", "onda interior", "segundo fôlego", "soco rápido"],
        "habilidade": {"nome": "Equilíbrio", "descricao": "Recupera energia a cada turno.", "mods": {"energia_turno": 8}},
        "formas": [{"nome": "Mestre do Vento", "elemento": "ar", "descricao": "Acelera os movimentos e fortalece as técnicas.",
                    "bonus": {"dano": 1.15, "esquiva": 20, "energia_turno": 10}, "ataques": ["onda interior", "soco rápido"]}]},
    "cavaleiro negro": {"vida": 130, "energia": 100, "velocidade": 35, "critico": 12, "defesa": 12, "escudo": 65,
        "elemento": "sombra", "ataques": ["corte sombrio", "corte", "corte duplos", "espada"],
        "habilidade": {"nome": "Aura negra", "descricao": "Drena parte do dano causado.", "mods": {"vampirismo": .10}},
        "formas": [{"nome": "Soberano das Trevas", "elemento": "sombra", "descricao": "A aura sombria aumenta o dano e a drenagem de vida.",
                    "bonus": {"dano": 1.2, "vampirismo": 0.15}, "ataques": ["corte sombrio", "corte duplos"]}]},
    "alquimista": {"vida": 90, "energia": 125, "velocidade": 60, "critico": 8, "defesa": 0, "escudo": 35,
        "elemento": "veneno", "ataques": ["poção corrosiva", "frasco ácido", "névoa pegajosa", "explosão instável"],
        "habilidade": {"nome": "Mistura instável", "descricao": "Especialista em efeitos de estado.", "mods": {"resist_status": 15}},
        "formas": [{"nome": "Químico Tóxico", "elemento": "veneno", "descricao": "Potencializa o dano e a duração das toxinas.",
                    "bonus": {"dano": 1.2}, "ataques": ["poção corrosiva", "explosão instável"],
                    "habilidade": {"nome": "Toxina Concentrada", "descricao": "Os ataques têm chance de envenenar o alvo.",
                                   "mods": {"on_hit": {"efeito": "veneno", "duracao": 2, "chance": 35}}}}]},
    "tanque": {"vida": 160, "energia": 90, "velocidade": 20, "critico": 4, "defesa": 18, "escudo": 100,
        "ataques": ["escudo pesado", "soco de pedra", "investida", "martelada"],
        "habilidade": {"nome": "Blindagem", "descricao": "Reduz dano recebido.", "mods": {"reducao": .15}},
        "formas": [{"nome": "Bastião de Aço", "elemento": "metal", "descricao": "Blindagem elevada e golpes de impacto reforçados.",
                    "bonus": {"reducao": 0.2, "defesa": 8}, "ataques": ["soco de pedra", "martelada"]}]},
})

INIMIGOS.update({
    "golem de pedra": {"artigo": "o", "elemento": "rocha", "vida": 130, "defesa": 20, "escudo": 35, "energia": 80, "velocidade": 25, "critico": 5,
        "ataques": ["deslizamento de pedra", "soco de pedra", "rolamento", "esmagar"], "acoes": ["atacar", "defender", "contrato", "fugir"], "contratos": list(CONTRATOS),
        "habilidade": {"nome": "Guardião rochoso", "descricao": "Ativa terreno rochoso.", "mods": {"terreno_rocha": True}},
        "formas": [{"nome": "Golem de pedra venenoso", "elemento": "veneno", "ataques": ["espinhos venenosos"], "descricao": "Forma venenosa."}]},
    "golem de metal": {"artigo": "o", "elemento": "metal", "vida": 150, "defesa": 18, "escudo": 25, "energia": 95, "velocidade": 30, "critico": 5,
        "ataques": ["metal cannon", "martelo metálico", "estouro metálico", "soco de metal"], "acoes": ["atacar", "defender", "transformar", "contrato"], "contratos": list(CONTRATOS),
        "habilidade": {"nome": "Metal protect", "descricao": "Reduz dano recebido.", "mods": {"reducao": .15}},
        "formas": [{"nome": "Ilhéu vulcânico metálico", "elemento": "fogo", "ataques": ["canhão vulcânico"], "descricao": "Forma ígnea."}]},
    "copiador": {"artigo": "o", "elemento": "neutro", "vida": 100, "defesa": 10, "escudo": 25, "energia": 100, "velocidade": 60, "critico": 10,
        "ataques": ["disparo preciso", "corte", "raio arcano", "mordida feroz"], "acoes": ["atacar", "transformar", "contrato"], "contratos": list(CONTRATOS),
        "habilidade": {"nome": "Cópia", "descricao": "Copia técnicas disponíveis.", "mods": {"dano": 1.1}}},
    "atiradora": {"artigo": "a", "elemento": "neutro", "vida": 95, "defesa": 8, "escudo": 50, "energia": 120, "velocidade": 55, "critico": 18,
        "ataques": ["tiro prateado", "headshot", "tiro carregado", "seis disparos"], "acoes": ["atacar", "defender", "contrato", "transformar"], "contratos": list(CONTRATOS),
        "habilidade": {"nome": "Atiradora precisa", "descricao": "Alta precisão.", "mods": {"dano": 1.1}},
        "formas": [{"nome": "Atiradora precisa", "ataques": ["headshot"], "descricao": "Fica invisível na névoa.", "habilidade": {"nome": "Invisibilidade na névoa", "descricao": "Esquiva elevada na névoa.", "mods": {"esquiva": 30}}}]},
    "cavaleiro negro conquistador": {"artigo": "o", "elemento": "sombra", "vida": 180, "defesa": 22, "escudo": 65, "energia": 150, "velocidade": 45, "critico": 12,
        "ataques": ["avanço conquistador", "batida", "trovoada conquistadora", "batida pesada"], "acoes": ["atacar", "defender", "transformar", "contrato"], "contratos": list(CONTRATOS),
        "habilidade": {"nome": "Intimidar", "descricao": "Aterroriza adversários.", "mods": {"on_hit": {"efeito": "medo", "duracao": 1, "chance": 20}}},
        "formas": [{"nome": "Lendário cavaleiro negro", "ataques": ["vento conquistador"], "descricao": "Forma conquistadora."}]},
    "juiz": {"artigo": "o", "elemento": "luz", "vida": 100, "defesa": 10, "escudo": 50, "energia": 150, "velocidade": 55, "critico": 10,
        "ataques": ["martelada", "culpado", "suspeito", "inocentado", "ataque de luz"], "acoes": ["atacar", "defender", "transformar", "contrato"], "contratos": list(CONTRATOS),
        "habilidade": {"nome": "Tribunal", "descricao": "Julga os combatentes.", "mods": {"dano": 1.05}},
        "formas": [{"nome": "Juiz da luz supremo", "ataques": ["execução final"], "descricao": "Ordem do tribunal."}]},
    "king kobra": {"artigo": "o", "elemento": "veneno", "vida": 350, "defesa": 18, "escudo": 20, "energia": 200, "velocidade": 65, "critico": 12,
        "ataques": ["jato venenoso", "mordida venenosa", "olhar medonho"], "acoes": ["atacar", "defender", "curar", "transformar", "contrato"], "contratos": list(CONTRATOS),
        "habilidade": {"nome": "Venenosa", "descricao": "Veneno persistente.", "mods": {"resist_status": 20}},
        "formas": [{"nome": "O verdadeiro majestoso King Kobra", "ataques": ["veneno final"], "descricao": "Bioma ácido."}]},
    "samurai arrogante de katana duplas": {"artigo": "o", "elemento": "metal", "vida": 150, "defesa": 18, "escudo": 50, "energia": 120, "velocidade": 90, "critico": 15,
        "ataques": ["corte", "corte duplo", "intimidar", "corte X"], "acoes": ["atacar", "defender", "transformar", "contrato"], "contratos": list(CONTRATOS),
        "habilidade": {"nome": "Fúria", "descricao": "Aumenta o dano.", "mods": {"dano": 1.15}},
        "formas": [{"nome": "Samurai com espírito guerreiro", "ataques": ["último slash"], "descricao": "Supreme aura."}]},
})
# Classificação interna (não é escolhida pelo jogador).
# Todos os inimigos listados aqui entram no mesmo sorteio aleatório.
# (lobo, slime, arqueiro bandido, fantasma e dragão existem, mas só aparecem se forem listados aqui.)
DIFICULDADES = {
    "fácil":   ["morcego", "ladrão", "goblin alquimista"],
    "médio":   ["esqueleto guerreiro", "golem de gelo"],
    "difícil": ["mestre mago", "supremo velocista", "necromante", "espadashim arrogante"],
}
DIFICULDADES["médio"].extend(["golem de pedra", "golem de metal", "atiradora"])
DIFICULDADES["difícil"].extend(["cavaleiro negro conquistador", "juiz", "samurai arrogante de katana duplas"])
DIFICULDADES["especial"] = ["king kobra"]

# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================
def normalizar(texto):
    # minúsculo e sem acento (permite digitar "pocao" no lugar de "poção")
    texto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def achar_nome(texto, opcoes):
    """
    Encontra uma opção pelo texto digitado.
    Aceita o nome completo ou um pedaço (3+ letras) que identifique só uma opção.
    Retorna None se não achar ou se for ambíguo.
    """
    alvo = normalizar(texto)

    for nome in opcoes:
        if normalizar(nome) == alvo:
            return nome

    if len(alvo) >= 3:
        candidatas = [nome for nome in opcoes if alvo in normalizar(nome)]
        if len(candidatas) == 1:
            return candidatas[0]

    return None


def perguntar(prompt, opcoes):
    while True:
        escolha = achar_nome(input(prompt), opcoes)

        if escolha is not None:
            return escolha

        print("Opção inválida.")


def sorteio(percentual):
    return random.random() * 100 < percentual


def criar_efeitos():
    return {nome_efeito: 0 for nome_efeito in EFEITOS}


# =====================================================
# ESTADO DA BATALHA
# =====================================================
herois = []
inimigos_lista = []
inventario = {}
clima = {"tipo": "limpo", "restam": 0}
terreno = {"nome": "Campo comum", "restam": 0, "criador": None}
estado = {"resultado": None}
invocacao_estado = {"usada": False}
INVOCAVEIS = {
    "morcego azul": {"elemento": "sombra", "vida": 32, "defesa": 4, "velocidade": 55, "energia": 25, "ataques": ["morcego_mordida"]},
    "morcego rosa": {"elemento": "sombra", "vida": 28, "defesa": 3, "velocidade": 65, "energia": 25, "ataques": ["mordida venenosa"]},
    "lobo alfa": {"elemento": "neutro", "vida": 75, "defesa": 12, "velocidade": 95, "energia": 45, "ataques": ["mordida feroz"]},
    "espírito de fogo": {"elemento": "fogo", "vida": 58, "defesa": 8, "velocidade": 70, "energia": 45, "ataques": ["lâmina flamejante"]},
}

BUFF_NOMES = {"forca": "força", "aleatorio": "efeito aleatório"}


def equipar_reliquia(c, nome, dados_reliquia):
    """Equipa uma relíquia: ajusta a vida máxima e guarda os modificadores."""
    c["reliquia"] = dict(dados_reliquia, nome=nome)

    nova_vida = max(1, round(c["vida_maxima"] * (1 + dados_reliquia.get("vida_max", 0))))

    c["vida_maxima"] = nova_vida
    c["vida"] = nova_vida
    c["cura_restante"] = nova_vida * CURA_INIMIGO["limite_total"]
    mods_reliquia = dados_reliquia.get("mods", {})
    c["energia_maxima"] = round(c["energia_maxima"] * (1 + mods_reliquia.get("energia_max", 0)))
    c["energia"] = c["energia_maxima"]
    c["velocidade"] = round(c["velocidade"] * mods_reliquia.get("velocidade_mult", 1)) + mods_reliquia.get("velocidade", 0)
    c["escudo_max"] = round(c["escudo_max"] * mods_reliquia.get("escudo_mult", 1))
    c["escudo_vida"] = c["escudo_max"]
    if nome == "pingente da rejeição":
        c["escudo_max"] = c["escudo_vida"] = 0
        c["restricoes_elixir"] = False
        c["restricoes_pingente"] = True
    if mods_reliquia.get("terreno_infernal"):
        definir_clima("sol", CLIMA_DURACAO)
        definir_terreno("Terreno magmático")
    if nome == "amuleto da lua de sangue":
        definir_clima("lua_sangue", 999)


def novo_combatente(chave, dados, lado, nome):
    return {
        "chave": chave,
        "nome": nome,
        "artigo": dados.get("artigo", ""),
        "lado": lado,
        "vida": dados["vida"],
        "vida_maxima": dados["vida"],
        "defesa": dados.get("defesa", 0),
        "velocidade": dados["velocidade"],
        "energia": dados["energia"],
        "energia_maxima": dados["energia"],
        "critico": dados.get("critico", CRITICO["chance_padrao"]),
        "ataques": list(dados["ataques"]),
        "acoes": list(dados.get("acoes", [])),
        # Alguns invocáveis não têm habilidade própria; mantenha o formato
        # consistente para os trechos que consultam habilidade.mods.
        "habilidade": dados.get("habilidade") or {},
        "formas": dados.get("formas", []),
        "forma_vida_pct": dados.get("forma_vida_pct", 50),
        "forma_estado": {"ativa": False, "restam": 0, "usada": False, "atual": None},
        "elemento": dados.get("elemento", "neutro"),
        "fraquezas": list(dados.get("fraquezas", [])),
        "resistencias": list(dados.get("resistencias", [])),
        "anulacoes": list(dados.get("anulacoes", [])),
        "contador": 0,
        "contratos": list(dados.get("contratos", [])),
        "contrato": None,
        "reliquia": None,
        "efeitos": criar_efeitos(),
        "defendendo": False,
        "escudo_vida": dados.get("escudo", 0),
        "escudo_max": dados.get("escudo", 0),
        "escudo_recarga": 0,
        "imunidade": 0,
        "carregando": None,
        "barreira": {"valor": 0, "restam": 0},
        "buffs": {"forca": 0, "aleatorio": 0},
        "elemental_marks": set(),
        "copiador_usou": False,
        "inventario_roubado": {},
        "cura_restante": dados["vida"] * CURA_INIMIGO["limite_total"],
        "fugiu": False,
        "morto": False,
    }


def r(c):
    # nome no meio da frase ("o morcego" / "Murilo")
    if c["lado"] == "heroi" or not c["artigo"]:
        return c["nome"]

    return f"{c['artigo']} {c['nome']}"


def R(c):
    # nome no começo da frase ("O morcego" / "Murilo")
    texto = r(c)
    return texto[0].upper() + texto[1:]


def todos():
    return herois + inimigos_lista


def vivos(lado):
    lista = herois if lado == "heroi" else inimigos_lista
    return [c for c in lista if c["vida"] > 0 and not c["fugiu"]]


def oposto(c):
    return "inimigo" if c["lado"] == "heroi" else "heroi"


# =====================================================
# MODIFICADORES, ESQUIVA, CRÍTICO E CLIMA
# =====================================================
MODS_PADRAO = {
    "dano": 1.0, "reducao": 0.0, "defesa": 0, "critico": 0, "esquiva": 0,
    "energia_turno": 0, "vida_turno": 0, "vampirismo": 0.0, "espinhos": 0.0, "perfura": 0.0,
    "resist_status": 0,
}


def mods(c):
    """Soma habilidade + mega forma + relíquia + contrato + itens + medo em um único dicionário."""
    m = dict(MODS_PADRAO)
    m["furia"] = []
    m["contra"] = None
    m["on_hit"] = None

    fontes = []

    if c.get("habilidade"):
        fontes.append(c["habilidade"].get("mods", {}))

    if c.get("reliquia"):
        fontes.append(c["reliquia"].get("mods", {}))

    if c.get("contrato"):
        fontes.append(c["contrato"].get("mods", {}))

    fe = c["forma_estado"]

    if fe["ativa"] and fe["atual"]:
        fontes.append(fe["atual"].get("bonus", {}))

        if fe["atual"].get("habilidade"):
            fontes.append(fe["atual"]["habilidade"].get("mods", {}))

    for fonte in fontes:
        for chave, valor in fonte.items():

            if chave == "dano":
                m["dano"] *= valor
            elif chave == "reducao":
                m["reducao"] = 1 - (1 - m["reducao"]) * (1 - valor)
            elif chave == "furia":
                m["furia"].append(valor)
            elif chave == "contra":
                m["contra"] = valor
            elif chave == "on_hit":
                m["on_hit"] = valor
            elif chave in m:
                m[chave] += valor

    porcentagem = c["vida"] / c["vida_maxima"] * 100

    for furia in m["furia"]:
        if porcentagem <= furia["vida_pct"]:
            m["dano"] *= furia["dano"]

    if c["buffs"]["forca"] > 0:
        m["dano"] *= ITENS["poção de força"]["multiplicador"]

    if c["efeitos"]["medo"] > 0:
        m["dano"] *= EFEITOS["medo"]["dano"]
    m["dano"] *= c.get("dano_item_mult", 1)

    return m


# =====================================================
# ELEMENTOS, FRAQUEZAS, RESISTÊNCIAS E ANULAÇÃO
# =====================================================
def nome_elemento(elemento):
    if elemento == "neutro":
        return "sem elemento"
    if elemento == "raio":
        return "elétrico"
    return elemento


def elemento_defensivo(c):
    # a mega forma pode mudar o elemento do personagem
    fe = c["forma_estado"]

    if fe["ativa"] and fe["atual"] and fe["atual"].get("elemento"):
        return fe["atual"]["elemento"]

    return c["elemento"]


def elemento_ataque(c, ataque):
    if ataque.get("elemento"):
        return ataque["elemento"]
    if (c.get("reliquia") or {}).get("mods", {}).get("espada_elemental"):
        elem = {"chuva": "agua", "sol": "fogo", "neve": "gelo", "tempestade": "raio", "chuva_trovoada": "raio", "chuva_tempestade": "ar", "ventania": "ar"}.get(clima["tipo"])
        if elem and ataque.get("dano", 0) > 0:
            return elem

    # na mega forma elemental, os ataques sem elemento ganham o elemento da forma
    fe = c["forma_estado"]

    if fe["ativa"] and fe["atual"] and fe["atual"].get("elemento") and ataque.get("dano", 0) > 0:
        return fe["atual"]["elemento"]

    return "neutro"


def mult_elemento(alvo, elemento):
    """Retorna (multiplicador, etiqueta) do elemento contra o alvo."""
    elemento = elemento or "neutro"
    tabela = ELEMENTOS.get(elemento_defensivo(alvo), {})

    fraco = set(tabela.get("fraco_a", [])) | set(alvo["fraquezas"])
    resiste = set(tabela.get("resiste", [])) | set(alvo["resistencias"])
    anula = set(tabela.get("anula", [])) | set(alvo["anulacoes"])

    # as listas próprias do personagem têm prioridade sobre a tabela
    fraco -= set(alvo["resistencias"])
    resiste -= set(alvo["fraquezas"])

    if elemento in anula:
        return 0.0, "anulacao"

    mult = 1.0
    etiqueta = None

    if elemento in fraco:
        mult *= ELEMENTO_MULT["fraqueza"]
        etiqueta = "fraqueza"

    if elemento in resiste:
        mult *= ELEMENTO_MULT["resistencia"]
        etiqueta = "resistencia"

    return mult, etiqueta


def texto_afinidades(c):
    fraco, resiste, anula = [], [], []

    for elemento in ELEMENTOS:
        mult, etiqueta = mult_elemento(c, elemento)

        if etiqueta == "anulacao":
            anula.append(nome_elemento(elemento))
        elif mult > 1:
            fraco.append(nome_elemento(elemento))
        elif mult < 1:
            resiste.append(nome_elemento(elemento))

    partes = []

    if fraco:
        partes.append("fraco a " + ", ".join(fraco))
    if resiste:
        partes.append("resiste a " + ", ".join(resiste))
    if anula:
        partes.append("anula " + ", ".join(anula))

    return "; ".join(partes) if partes else "sem fraquezas"


# =====================================================
# ATAQUES ESPECIAIS (CONTADOR) E CONTRATOS
# =====================================================
def ataques_do(c):
    # ataques da classe/inimigo + ataques exclusivos da mega forma ativa
    lista = list(c["ataques"])
    fe = c["forma_estado"]

    if fe["ativa"] and fe["atual"]:
        for nome in fe["atual"].get("ataques", []):
            if nome not in lista:
                lista.append(nome)

    return lista


def ataque_disponivel(c, nome):
    # ataque especial: precisa de N ataques feitos antes
    return c["contador"] >= ATAQUES[nome].get("requer", 0)


def registrar_uso(c, nome):
    ataque = ATAQUES[nome]

    if ataque.get("requer"):
        c["contador"] = 0
    elif not ataque.get("util"):
        c["contador"] += 1


def restringe(c, tipo):
    return bool(c["contrato"]) and tipo in c["contrato"]["restringe"]


def assinar_contrato(c, nome):
    c["contrato"] = dict(CONTRATOS[nome], nome=nome)

    print(f"{R(c)} assinou o {nome}!")
    print(f"  - {CONTRATOS[nome]['descricao']}")
    print(f"  - Com um contrato, {r(c)} não pode mais usar mega forma.")


def mult_clima(elemento):
    if not elemento:
        return 1.0

    return CLIMAS[clima["tipo"]]["elementos"].get(elemento, 1.0)


def definir_terreno(nome, duracao=5, criador=None):
    terreno["nome"], terreno["restam"], terreno["criador"] = nome, duracao, criador
    print(f"Terreno ativo: {nome} por {duracao} rodadas.")


COMBINACOES_ELEMENTAIS = {
    "agua + gelo": ("congelado", None), "agua + eletrico": ("paralisado", None),
    "planta + fogo": ("queima", None), "gas + fogo": ("queima", None),
    "gas + veneno": ("veneno", None), "gas + agua": (None, "Terreno de névoa"),
    "terra + agua": ("afundado", "Terreno de lama"), "gas + eletrico": ("queima", None),
    "fantasma + sombrio": ("medo", None), "ar + fogo": ("queima", None),
    "ar + terra": (None, "Tempestade de terra"),
    "ar + gas + veneno": (None, "Terreno de gás venenoso"),
    "ar + gas + fogo": (None, "Terreno de gás inflamável"),
    "ar + gas + agua": (None, "Terreno de névoa"),
}


def aplicar_combinacao(combinacao, alvos=None):
    chave = normalizar(combinacao).replace("á", "a").replace("é", "e")
    if chave == "chuva + tempestade":
        definir_clima("chuva_tempestade", CLIMA_DURACAO)
        return
    if chave == "chuva + trovoada":
        definir_clima("chuva_trovoada", CLIMA_DURACAO)
        return
    efeito, terreno_resultante = COMBINACOES_ELEMENTAIS.get(chave, (None, None))
    if terreno_resultante:
        definir_terreno(terreno_resultante)
    if efeito:
        for alvo in alvos or vivos("inimigo"):
            aplicar_efeito(alvo, efeito, 2)
    if not efeito and not terreno_resultante:
        print(f"Combinação desconhecida: {combinacao}.")


def chance_esquiva_c(c):
    chance = min(ESQUIVA["maximo"], c["velocidade"] / ESQUIVA["divisor"])
    chance += mods(c)["esquiva"]

    if c["efeitos"]["lento"] > 0:
        chance /= 2

    cfg = CLIMAS[clima["tipo"]]
    chance = chance * cfg.get("esquiva_mult", 1) + cfg.get("esquiva_bonus", 0)
    if "nevoa" in normalizar(terreno["nome"]):
        chance += 35

    return max(0, min(ESQUIVA["limite"], chance))


def defesa_c(c):
    return c["defesa"] + mods(c)["defesa"]


def critico_c(c):
    return c["critico"] + mods(c)["critico"]


def curar(c, quantidade):
    # sangramento reduz a cura recebida
    if c["efeitos"]["sangramento"] > 0:
        quantidade *= EFEITOS["sangramento"]["cura"]

    antes = c["vida"]
    c["vida"] = min(c["vida_maxima"], round(c["vida"] + quantidade, 2))

    return round(c["vida"] - antes, 2)


def definir_clima(tipo, duracao):
    anterior = clima["tipo"]
    if anterior == "chuva" and tipo == "tempestade":
        tipo = "chuva_tempestade"
    elif anterior == "chuva" and tipo == "trovoada":
        tipo = "chuva_trovoada"
    clima["tipo"] = tipo
    clima["restam"] = duracao

    cfg = CLIMAS[tipo]
    print(f"O clima mudou: {cfg['nome']}! {cfg['descricao']} (dura {duracao} rodadas)")


# =====================================================
# EFEITOS DE STATUS
# =====================================================
def aplicar_efeito(alvo, efeito, duracao):
    if alvo["vida"] <= 0 or alvo["imunidade"] > 0:
        return False

    # resistência a efeitos (relíquias)
    resistencia = mods(alvo)["resist_status"]

    if resistencia > 0 and sorteio(resistencia):
        print(f"{R(alvo)} resistiu ao efeito {efeito}!")
        return False

    # se já estiver com o efeito, mantém a maior duração
    alvo["efeitos"][efeito] = max(alvo["efeitos"][efeito], duracao)

    print(f"{R(alvo)} ficou {EFEITOS[efeito]['estado']} por {duracao} turno(s).")
    return True


def processar_efeitos_inicio(c):
    """
    Roda no início do turno. Retorna True se pode agir
    e False se perdeu o turno (paralisado/congelado/lento).
    """
    pode_agir = True

    for efeito, cfg in EFEITOS.items():

        if c["efeitos"][efeito] <= 0:
            continue

        if cfg["tipo"] == "dano":
            dano = round(cfg["dano"] * mult_clima(cfg.get("elemento")), 2)
            c["vida"] = max(0, round(c["vida"] - dano, 2))
            print(f"{R(c)} sofreu {dano} de dano de {efeito}.")

        elif cfg["tipo"] == "impede":
            print(f"{R(c)} está {cfg['estado']} e não pode agir!")
            pode_agir = False

        elif cfg["tipo"] == "lento":
            if sorteio(cfg["chance"]):
                print(f"{R(c)} está lento demais e perdeu o turno!")
                pode_agir = False
            else:
                print(f"{R(c)} está lento, mas conseguiu agir.")

        elif cfg["tipo"] == "medo":
            print(f"{R(c)} está com medo e causa menos dano.")

        c["efeitos"][efeito] -= 1

        if c["efeitos"][efeito] == 0:
            print(f"O efeito {efeito} em {r(c)} acabou.")

    return pode_agir


# =====================================================
# MORTE E RESSURREIÇÃO
# =====================================================
def tentar_ressuscitar(c):
    if inventario["ressusitador"] <= 0:
        return False

    inventario["ressusitador"] -= 1
    print(f"\n{R(c)} usou o ressusitador no último instante!")

    if random.randint(1, 100) <= RESSUSCITADOR["chance"]:

        c["vida"] = c["vida_maxima"] * RESSUSCITADOR["vida_percentual"]
        c["imunidade"] = RESSUSCITADOR["imunidade"]

        for nome_efeito in c["efeitos"]:
            c["efeitos"][nome_efeito] = 0

        print(
            f"{R(c)} ressuscitou com {c['vida']} de vida "
            f"e ficará imune por {RESSUSCITADOR['imunidade']} rodada(s)!"
        )
        return True

    print("O ressusitador falhou...")
    return False


def checar_morte(c):
    """Retorna True se o combatente morreu de vez."""
    if c["morto"]:
        return True

    if c["vida"] > 0:
        return False

    c["vida"] = 0

    if c["lado"] == "heroi" and tentar_ressuscitar(c):
        return False

    c["morto"] = True
    c["carregando"] = None
    print(f"{R(c)} foi derrotado!")
    return True


# =====================================================
# DANO
# =====================================================
def calcular_golpe(atacante, ataque, elemento):
    base = ataque["dano"]
    rolagem = random.choice(dado)
    bruto = base + base * rolagem / 10

    critico = sorteio(critico_c(atacante))

    if critico:
        bruto *= CRITICO["multiplicador"]

    bruto *= mods(atacante)["dano"]
    bruto *= mult_clima(elemento)
    terreno_nome = normalizar(terreno["nome"])
    tipo = elemento_defensivo(atacante)
    if ("planta" in terreno_nome and tipo == "planta") or (("ground terrain" in terreno_nome or "terreno comum" in terreno_nome) and tipo == "terra") or (("eletrico" in terreno_nome or "electric terrain" in terreno_nome) and tipo in ("raio", "eletrico")):
        bruto *= 1.1

    return round(bruto), critico, rolagem


def receber_dano(atacante, alvo, bruto):
    """
    Aplica defesa, redução, defesa do inimigo, barreira e escudo.
    Retorna o dano que chegou na vida.
    """
    m_atacante = mods(atacante)
    m_alvo = mods(alvo)

    defesa = max(0, defesa_c(alvo) * (1 - m_atacante["perfura"]))
    dano = max(0, bruto - defesa)
    dano *= (1 - m_alvo["reducao"])

    # inimigo que estava se defendendo recebe metade do dano
    if alvo["defendendo"] and alvo["lado"] == "inimigo":
        dano *= 0.5
        alvo["defendendo"] = False
        print(f"{R(alvo)} estava se defendendo!")

    dano = round(dano, 2)

    if dano <= 0:
        print(f"O golpe não causou dano em {r(alvo)}.")
        return 0

    # barreira (habilidade de proteção)
    if alvo["barreira"]["valor"] > 0:

        absorvido = round(min(alvo["barreira"]["valor"], dano), 2)
        alvo["barreira"]["valor"] = round(alvo["barreira"]["valor"] - absorvido, 2)
        dano = round(dano - absorvido, 2)

        print(f"A barreira de {r(alvo)} absorveu {absorvido} de dano.")

        if alvo["barreira"]["valor"] <= 0:
            alvo["barreira"]["valor"] = 0
            print(f"A barreira de {r(alvo)} se quebrou!")

    # escudo dos heróis
    if alvo["defendendo"] and alvo["lado"] == "heroi" and dano > 0:

        absorvido = round(min(alvo["escudo_vida"], dano * ESCUDO["absorcao"]), 2)
        alvo["escudo_vida"] = round(alvo["escudo_vida"] - absorvido, 2)
        dano = round(dano - absorvido, 2)

        print(f"O escudo de {r(alvo)} absorveu {absorvido} de dano.")

        if alvo["escudo_vida"] <= 0:
            alvo["escudo_vida"] = 0
            alvo["escudo_recarga"] = ESCUDO["recarga"]
            print(f"O escudo de {r(alvo)} quebrou! Ele volta em {ESCUDO['recarga']} turno(s).")

    if dano <= 0:
        return 0

    alvo["vida"] = max(0, round(alvo["vida"] - dano, 2))

    print(f"{R(alvo)} sofreu {dano} de dano. Vida: {alvo['vida']}/{alvo['vida_maxima']}.")

    # vampirismo do atacante
    if m_atacante["vampirismo"] > 0 and atacante["vida"] > 0:
        ganho = curar(atacante, dano * m_atacante["vampirismo"])
        if ganho > 0:
            print(f"{R(atacante)} recuperou {ganho} de vida com o golpe.")

    # espinhos do alvo
    if m_alvo["espinhos"] > 0 and atacante["vida"] > 0:
        refletido = round(dano * m_alvo["espinhos"], 2)
        atacante["vida"] = max(0, round(atacante["vida"] - refletido, 2))
        print(f"{R(atacante)} sofreu {refletido} de dano refletido!")
        checar_morte(atacante)

    # contra-golpe do alvo
    contra = m_alvo["contra"]

    if contra and alvo["vida"] > 0 and atacante["vida"] > 0 and sorteio(contra["chance"]):
        atacante["vida"] = max(0, round(atacante["vida"] - contra["dano"], 2))
        print(f"{R(alvo)} contra-atacou! {R(atacante)} sofreu {contra['dano']} de dano.")
        checar_morte(atacante)

    checar_morte(alvo)

    return dano


def dano_direto(alvo, dano, elemento=None):
    """
    Dano de bombas, pedras e raios: ignora defesa e barreira, mas respeita
    elemento e clima. Retorna False se o alvo anulou o dano.
    """
    if elemento:

        mult, etiqueta = mult_elemento(alvo, elemento)

        if etiqueta == "anulacao":
            print(f"{R(alvo)} anulou o ataque ({nome_elemento(elemento)})!")
            return False

        dano = round(dano * mult_clima(elemento) * mult, 2)

        if etiqueta == "fraqueza":
            print("É super efetivo!")
        elif etiqueta == "resistencia":
            print(f"{R(alvo)} resistiu ao elemento {nome_elemento(elemento)}.")

    alvo["vida"] = max(0, round(alvo["vida"] - dano, 2))
    print(f"{R(alvo)} sofreu {dano} de dano. Vida: {alvo['vida']}/{alvo['vida_maxima']}.")
    checar_morte(alvo)

    return True


def atingir(atacante, alvo, ataque):
    """Um golpe contra um alvo: imunidade, esquiva, elemento, crítico, dano, dreno e efeitos."""
    if alvo["imunidade"] > 0:
        print(f"{R(alvo)} está imune e não sofreu nada!")
        return

    if sorteio(chance_esquiva_c(alvo)):
        print(f"{R(alvo)} esquivou!")
        return

    elemento = elemento_ataque(atacante, ataque)
    mult, etiqueta = mult_elemento(alvo, elemento)

    # anulação: o ataque inteiro (dano e efeitos) é anulado
    if etiqueta == "anulacao":
        print(f"{R(alvo)} anulou o ataque ({nome_elemento(elemento)})!")
        return

    if ataque["dano"] > 0:

        bruto, critico, rolagem = calcular_golpe(atacante, ataque, elemento)
        print(f"Dado: {rolagem}/10 | dano calculado com modificadores: {round(bruto)}.")

        if critico:
            print("CRÍTICO!")

        if etiqueta == "fraqueza":
            print("É super efetivo!")
        elif etiqueta == "resistencia":
            print(f"{R(alvo)} resistiu ao elemento {nome_elemento(elemento)}.")

        mult *= alvo.get("vulnerabilidades", {}).get(elemento, 1)
        if (atacante.get("reliquia") or {}).get("mods", {}).get("dano_espadas") and any(t in alvo["chave"] for t in ("espad", "samurai", "cavaleiro negro")):
            mult *= atacante["reliquia"]["mods"]["dano_espadas"]
        causado = receber_dano(atacante, alvo, round(bruto * mult))
        if (atacante.get("reliquia") or {}).get("mods", {}).get("roubo"):
            nome_roubado = random.choice(list(ITENS))
            if inventario.get(nome_roubado, 0) > 0:
                inventario[nome_roubado] -= 1
            roubados = atacante["inventario_roubado"]
            roubados[nome_roubado] = roubados.get(nome_roubado, 0) + 1
            print(f"{R(atacante)} roubou {nome_roubado} de {R(alvo)}!")
        if critico and alvo["vida"] <= 0 and alvo["chave"] == "gojo":
            print(f"Pra que dar crítico no {R(alvo)} Arrogante!")

        if ataque.get("drena") and causado > 0 and atacante["vida"] > 0:
            ganho = curar(atacante, causado * ataque["drena"])
            print(f"{R(atacante)} drenou {ganho} de vida!")

    if alvo["vida"] <= 0:
        return

    # efeito do próprio ataque
    efeito = ataque.get("efeito")

    if efeito and sorteio(ataque.get("chance", 100)):
        aplicar_efeito(alvo, efeito, ataque["duracao"])

    # habilidade que aplica efeito ao acertar
    on_hit = mods(atacante)["on_hit"]

    if on_hit and sorteio(on_hit.get("chance", 100)):
        aplicar_efeito(alvo, on_hit["efeito"], on_hit["duracao"])

    if atacante["chave"] == "copiador" and not atacante["copiador_usou"]:
        atacante["ataques"] = list(alvo["ataques"][:4])
        atacante["habilidade"] = alvo.get("habilidade")
        atacante["formas"] = list(alvo.get("formas", []))
        atacante["defesa"] = alvo["defesa"]
        atacante["elemento"] = elemento_defensivo(alvo)
        atacante["vida_maxima"] = alvo["vida_maxima"]
        atacante["vida"] = min(atacante["vida"], atacante["vida_maxima"])
        atacante["energia_maxima"] = alvo["energia_maxima"]
        atacante["energia"] = min(atacante["energia"], atacante["energia_maxima"])
        atacante["velocidade"] = alvo["velocidade"]
        atacante["copiador_usou"] = True
        print(f"{R(atacante)} copiou atributos, ataques e formas de {R(alvo)}!")

    if elemento not in ("neutro", "none"):
        marca = {"sombra": "sombrio", "raio": "eletrico"}.get(elemento, elemento)
        alvo["elemental_marks"].add(marca)
        for combinacao in COMBINACOES_ELEMENTAIS:
            ingredientes = set(combinacao.split(" + "))
            if ingredientes.issubset(alvo["elemental_marks"]):
                aplicar_combinacao(combinacao, [alvo])
                break

    # poção de efeito aleatório
    if atacante["buffs"]["aleatorio"] > 0:
        aplicar_efeito(
            alvo,
            random.choice(list(EFEITOS)),
            ITENS["poção de efeito aleatório"]["efeito_duracao"]
        )


def usar_ataque(atacante, nome_ataque, alvos):
    ataque = ATAQUES[nome_ataque]

    for alvo in alvos:

        if alvo["vida"] <= 0 or alvo["fugiu"]:
            continue

        for _ in range(ataque.get("golpes", 1)):

            if alvo["vida"] <= 0:
                break

            atingir(atacante, alvo, ataque)

        if atacante["vida"] <= 0:
            break


def usar_util(c, alvo, ataque):
    """Ataques sem dano: clima, proteção e cura."""
    util = ataque["util"]

    if "clima" in util:
        definir_clima(util["clima"], CLIMA_DURACAO)

    if "protecao" in util:
        alvo["barreira"] = {"valor": util["protecao"], "restam": util["rodadas"] + 1}
        print(f"{R(alvo)} ganhou uma barreira de {util['protecao']} por {util['rodadas']} rodada(s).")

    if "cura" in util:
        ganho = curar(alvo, util["cura"])
        print(f"{R(alvo)} recuperou {ganho} de vida ({alvo['vida']}/{alvo['vida_maxima']}).")


# =====================================================
# MEGA FORMAS
# =====================================================
def ativar_forma(c, forma):
    fe = c["forma_estado"]

    fe["ativa"] = True
    fe["usada"] = True
    fe["atual"] = forma
    fe["restam"] = FORMAS["duracao"] + 1   # o turno da transformação não conta

    titulo = forma["nome"]

    if forma.get("letra"):
        titulo += f" ({forma['letra']})"

    print(f"{R(c)} liberou a mega forma {titulo} por {FORMAS['duracao']} turnos!")
    print(f"  - {forma['descricao']}")

    if forma.get("elemento"):
        print(f"  - Elemento: {forma['elemento']} ({texto_afinidades(c)})")

    if forma.get("ataques"):
        print(f"  - Ataques exclusivos: {', '.join(forma['ataques'])}")

    if forma.get("habilidade"):
        print(f"  - Habilidade: {forma['habilidade']['nome']} — {forma['habilidade']['descricao']}")

    depois = forma.get("ao_transformar", {})

    if "cura" in depois:
        ganho = curar(c, c["vida_maxima"] * depois["cura"])
        print(f"  - {R(c)} recuperou {ganho} de vida.")

    if depois.get("energia_cheia"):
        c["energia"] = c["energia_maxima"]
        print(f"  - Energia recarregada.")

    if "clima" in depois:
        definir_clima(depois["clima"], CLIMA_DURACAO)

    if "aplica" in depois:
        for alvo in vivos(oposto(c)):
            aplicar_efeito(alvo, depois["aplica"]["efeito"], depois["aplica"]["duracao"])


def aplicar_por_turno(c, forma):
    por_turno = forma.get("por_turno")

    if not por_turno:
        return

    if "aplica" in por_turno:
        for alvo in vivos(oposto(c)):
            aplicar_efeito(alvo, por_turno["aplica"]["efeito"], por_turno["aplica"]["duracao"])

    if "cura" in por_turno:
        ganho = curar(c, por_turno["cura"])
        print(f"A mega forma regenera {ganho} de vida de {r(c)} ({c['vida']}/{c['vida_maxima']}).")


# =====================================================
# INÍCIO E FIM DE TURNO
# =====================================================
def inicio_de_turno(c):
    """Retorna True se o combatente pode agir neste turno."""
    m = mods(c)

    habilidade = c.get("habilidade") or {}
    habilidade_mods = habilidade.get("mods") or {}
    if habilidade_mods.get("terreno_rocha") and terreno["nome"] == "Campo comum":
        definir_terreno("Terreno rochoso", 5, c)

    if clima["tipo"] == "ventania" and c["lado"] == "inimigo" and c["elemento"] != "ar" and c["vida"] > 0:
        aplicar_efeito(c, "lento", 1)

    # recupera energia
    c["energia"] = min(c["energia_maxima"], c["energia"] + REGEN_ENERGIA + m["energia_turno"])

    # escudo dos heróis: recarga (se quebrado) ou regeneração
    if c["lado"] == "heroi" and c["escudo_max"] > 0:

        if c["escudo_recarga"] > 0:

            c["escudo_recarga"] -= 1

            if c["escudo_recarga"] == 0:
                c["escudo_vida"] = c["escudo_max"] * ESCUDO["vida_ao_voltar"]
                print(f"O escudo de {r(c)} se recuperou e voltou com {c['escudo_vida']} de vida.")

        elif c["escudo_vida"] < c["escudo_max"]:
            c["escudo_vida"] = min(c["escudo_max"], c["escudo_vida"] + ESCUDO["regeneracao"])

    # efeitos da mega forma
    fe = c["forma_estado"]

    if fe["ativa"]:
        aplicar_por_turno(c, fe["atual"])

    if m["vida_turno"]:
        curar(c, m["vida_turno"])

    # efeitos de status
    pode_agir = processar_efeitos_inicio(c)

    if c["vida"] <= 0:

        if checar_morte(c):
            return False

        # ressuscitou: os efeitos foram removidos
        pode_agir = True

    return pode_agir


def fim_de_turno(c):
    for chave in c["buffs"]:

        if c["buffs"][chave] > 0:
            c["buffs"][chave] -= 1

            if c["buffs"][chave] == 0:
                print(f"O efeito de {BUFF_NOMES[chave]} em {r(c)} acabou.")

    barreira = c["barreira"]

    if barreira["valor"] > 0:
        barreira["restam"] -= 1

        if barreira["restam"] <= 0:
            barreira["valor"] = 0
            print(f"A barreira de {r(c)} desapareceu.")

    fe = c["forma_estado"]

    if fe["ativa"]:
        fe["restam"] -= 1

        if fe["restam"] <= 0:
            fe["ativa"] = False
            print(f"A mega forma de {r(c)} acabou.")


def fim_de_rodada():
    if terreno["restam"] > 0:
        for c in vivos("heroi") + vivos("inimigo"):
            tipo = elemento_defensivo(c)
            nome_terreno = normalizar(terreno["nome"])
            if "planta" in nome_terreno or "grass" in nome_terreno:
                if tipo == "planta" or terreno.get("criador") is c:
                    curar(c, c["vida_maxima"] * .02)
            elif "lama" in nome_terreno:
                if tipo != "terra": aplicar_efeito(c, "afundado", 1)
            elif "eletrico" in nome_terreno or "electric terrain" in nome_terreno:
                if tipo in ("raio", "eletrico"): c["velocidade"] = round(c["velocidade"] * 1.12)
                elif sorteio(10): aplicar_efeito(c, "paralisado", 1)
            elif "gas venenoso" in nome_terreno:
                if tipo == "veneno": curar(c, c["vida_maxima"] * .04)
                else: aplicar_efeito(c, "veneno", 1)
            elif "gas inflamavel" in nome_terreno:
                if tipo == "fogo": curar(c, c["vida_maxima"] * .04)
                else: aplicar_efeito(c, "queima", 1)
            elif "nevoa" in nome_terreno:
                c["efeitos"]["lento"] = max(c["efeitos"]["lento"], 1)
            elif "cemiterio" in nome_terreno and c["chave"] != "necromante":
                dano_direto(c, c["vida_maxima"] * .03)
            elif ("assombrado" in nome_terreno or "sombroso" in nome_terreno) and tipo not in ("sombra", "sombrio", "fantasma"):
                aplicar_efeito(c, "medo", 1); aplicar_efeito(c, "paralisado", 1)
            elif "rochoso" in nome_terreno:
                if tipo not in ("rocha", "raio", "eletrico"): aplicar_efeito(c, "lento", 1)
            elif "terreno de fogo" in nome_terreno or "burn terrain" in nome_terreno:
                if tipo != "fogo": aplicar_efeito(c, "queima", 1)
            elif "magmatico" in nome_terreno and tipo not in ("rocha", "fogo"):
                dano_direto(c, 8, "fogo"); aplicar_efeito(c, "queima", 1)
        terreno["restam"] -= 1
        if terreno["restam"] <= 0:
            terreno.update(nome="Campo comum", restam=0, criador=None)
            print("O terreno perdeu o efeito.")

    for c in todos():
        if c.get("vida_maximizada_turnos", 0):
            c["vida_maximizada_turnos"] -= 1
            if c["vida_maximizada_turnos"] == 0:
                c["vida_maxima"] = max(1, round(c["vida_maxima"] / 1.5))
                c["vida"] = min(c["vida"], c["vida_maxima"])
                print(f"O efeito maximador de {r(c)} acabou.")

    if clima["tipo"] == "limpo":
        cfg = {"apaga": [], "raio": 0}
    else:
        cfg = CLIMAS[clima["tipo"]]

    for efeito in cfg.get("apaga", []):
        for c in todos():
            if c["vida"] > 0 and c["efeitos"][efeito] > 0:
                c["efeitos"][efeito] = 0
                print(f"A {cfg['nome']} eliminou {efeito} de {r(c)}.")

    if cfg.get("raio"):

        candidatos = [c for c in todos() if c["vida"] > 0 and not c["fugiu"]]

        if candidatos:
            alvo = random.choice(candidatos)

            if alvo["imunidade"] > 0:
                print(f"Um raio caiu, mas {r(alvo)} está imune!")
            else:
                print(f"Um raio da tempestade cai sobre {r(alvo)}!")
                dano_direto(alvo, cfg["raio"])

    if clima["tipo"] != "limpo":
        clima["restam"] -= 1

    if clima["tipo"] != "limpo" and clima["restam"] <= 0:
        clima["tipo"] = "limpo"
        print("O clima voltou ao normal.")

    if not invocacao_estado["usada"] and any(e["chave"] in {"King Kobra", "king kobra", "mestre mago", "necromante", "cavaleiro negro conquistador"} for e in vivos("inimigo")) and sorteio(12):
        nome, dados = random.choice(list(INVOCAVEIS.items()))
        aliado = novo_combatente(nome, dados, "inimigo", nome)
        aliado["elemento"] = dados["elemento"]
        inimigos_lista.append(aliado)
        invocacao_estado["usada"] = True
        print(f"Um inimigo de alto nível invocou {R(aliado)}! Só uma invocação pode ficar em campo.")

# =====================================================
# TURNO DOS INIMIGOS (IA)
# =====================================================
def util_ok(c, nome):
    # ataques de utilidade só são usados quando fazem sentido
    util = ATAQUES[nome].get("util")

    if not util:
        return True

    if "protecao" in util and c["barreira"]["valor"] > 0:
        return False

    if "cura" in util and c["vida"] >= c["vida_maxima"]:
        return False

    if "clima" in util and clima["tipo"] == util["clima"]:
        return False

    return True


def continuar_carga(c):
    carga = c["carregando"]
    carga["restam"] -= 1

    if carga["restam"] > 0:
        print(f"{R(c)} continua carregando {carga['ataque']}...")
        return

    nome_ataque = carga["ataque"]
    ataque = ATAQUES[nome_ataque]
    c["carregando"] = None

    if ataque.get("area"):
        alvos = vivos(oposto(c))
    else:
        alvos = [a for a in carga["alvos"] if a["vida"] > 0 and not a["fugiu"]]

        if not alvos and vivos(oposto(c)):
            alvos = [random.choice(vivos(oposto(c)))]

    print(f"{R(c)} liberou {nome_ataque}!")
    usar_ataque(c, nome_ataque, alvos)


def acao_inimigo(c):
    porcentagem = c["vida"] / c["vida_maxima"] * 100

    print(
        f"{R(c)} está com {porcentagem:.0f}% de vida "
        f"({c['vida']}/{c['vida_maxima']}) e {c['energia']} de energia."
    )

    roubados = c.get("inventario_roubado", {})
    disponiveis_roubados = [nome for nome, quantidade in roubados.items() if quantidade > 0]
    if disponiveis_roubados and random.random() < .35:
        nome_item = random.choice(disponiveis_roubados)
        item = ITENS[nome_item]
        tipo = item["tipo"]
        roubados[nome_item] -= 1
        if tipo == "cura":
            ganho = curar(c, item.get("cura", 0))
            print(f"{R(c)} usou o item roubado {nome_item} e recuperou {ganho} de vida.")
            return
        if tipo == "energia":
            c["energia"] = min(c["energia_maxima"], c["energia"] + item.get("energia", 0))
            print(f"{R(c)} usou o item roubado {nome_item} e recuperou energia.")
            return
        if tipo in ("bomba", "pedra", "climatica"):
            alvo = random.choice(vivos("heroi"))
            dano = item.get("dano", CLIMAS[clima["tipo"]]["bomba"].get("dano", 20) if tipo == "climatica" else 0)
            dano_direto(alvo, dano, item.get("elemento"))
            if item.get("aplica") and alvo["vida"] > 0:
                aplicar_efeito(alvo, item["aplica"], item.get("duracao", 1))
            print(f"{R(c)} usou o item roubado {nome_item}!")
            return

    # filtra ações que não fazem sentido
    acoes = list(c["acoes"])

    possiveis = [
        nome for nome in ataques_do(c)
        if ATAQUES[nome]["energia"] <= c["energia"]
        and util_ok(c, nome)
        and ataque_disponivel(c, nome)
    ]

    # só ataca com o que a energia (e o contador especial) permitem
    if "atacar" in acoes and not possiveis:
        acoes.remove("atacar")

    # não se defende se já está defendendo (ou se o contrato proíbe)
    if "defender" in acoes and (c["defendendo"] or restringe(c, "defender")):
        acoes.remove("defender")

    # não cura com vida cheia, sem energia, sem cura restante ou com contrato que proíbe itens
    if "curar" in acoes:
        if (
            porcentagem >= 100
            or c["energia"] < CURA_INIMIGO["energia"]
            or c["cura_restante"] <= 0
            or restringe(c, "itens")
        ):
            acoes.remove("curar")

    # não foge com mais de 10% de vida
    if "fugir" in acoes and porcentagem > 10:
        acoes.remove("fugir")

    # só se transforma uma vez, com a vida abaixo do limite e sem contrato
    if "transformar" in acoes:
        if (
            not c["formas"]
            or c["forma_estado"]["usada"]
            or c["contrato"] is not None
            or porcentagem > c["forma_vida_pct"]
        ):
            acoes.remove("transformar")

    # só faz um contrato, antes de se transformar, com a vida abaixo de 85%
    if "contrato" in acoes:
        if (
            not c["contratos"]
            or c["contrato"] is not None
            or c["forma_estado"]["usada"]
            or porcentagem > 85
        ):
            acoes.remove("contrato")

    # com pouca energia (ou sem opção), descansa
    if not acoes:
        acoes.append("descansar")
    elif c["energia"] <= c["energia_maxima"] * 0.35 and not restringe(c, "descansar"):
        acoes.append("descansar")

    acao = random.choice(acoes)

    # ---------- ATACAR ----------
    if acao == "atacar":

        nome_ataque = random.choice(possiveis)
        ataque = ATAQUES[nome_ataque]

        c["energia"] -= ataque["energia"]
        registrar_uso(c, nome_ataque)

        if ataque.get("util"):

            print(f"{R(c)} usou {nome_ataque} e gastou {ataque['energia']} de energia.")
            usar_util(c, c, ataque)

        else:

            if ataque.get("area"):
                alvos = vivos("heroi")
            else:
                alvos = [random.choice(vivos("heroi"))]

            turnos_carga = int(ataque.get("carrega", 0) or (
                1 if (c.get("reliquia") or {}).get("nome") == "grande espada" and ataque.get("dano", 0) >= 35 else 0
            ))
            if turnos_carga:

                c["carregando"] = {
                    "ataque": nome_ataque,
                    "restam": turnos_carga,
                    "alvos": alvos,
                }

                print(
                    f"{R(c)} gastou {ataque['energia']} de energia e começou a "
                    f"carregar {nome_ataque}! Ele dispara em {turnos_carga} turno(s) dele."
                )

            else:

                print(f"{R(c)} usou {nome_ataque} e gastou {ataque['energia']} de energia.")
                usar_ataque(c, nome_ataque, alvos)

    # ---------- DEFENDER ----------
    elif acao == "defender":

        c["defendendo"] = True
        print(f"{R(c)} se defendeu.")

    # ---------- CURAR ----------
    elif acao == "curar":

        cura = round(
            min(
                c["vida_maxima"] * CURA_INIMIGO["percentual_por_uso"],
                c["vida_maxima"] - c["vida"],
                c["cura_restante"],
            ),
            2,
        )

        c["energia"] -= CURA_INIMIGO["energia"]
        ganho = curar(c, cura)
        c["cura_restante"] = round(c["cura_restante"] - cura, 2)

        print(
            f"{R(c)} gastou {CURA_INIMIGO['energia']} de energia, se curou {ganho} "
            f"e está com {c['vida']} de vida. Ainda pode curar até {c['cura_restante']}."
        )

    # ---------- TRANSFORMAR ----------
    elif acao == "transformar":

        ativar_forma(c, random.choice(c["formas"]))

    # ---------- CONTRATO ----------
    elif acao == "contrato":

        assinar_contrato(c, random.choice(c["contratos"]))

    # ---------- DESCANSAR ----------
    elif acao == "descansar":

        c["energia"] = min(c["energia_maxima"], c["energia"] + DESCANSO["energia"])
        print(f"{R(c)} descansou e recuperou energia ({c['energia']}/{c['energia_maxima']}).")

    # ---------- FUGIR ----------
    elif acao == "fugir":

        if random.randint(0, 10) >= 8:
            c["fugiu"] = True
            print(f"{R(c)} fugiu da batalha!")
        else:
            print(f"{R(c)} tentou fugir, mas não conseguiu.")


# =====================================================
# TURNO DOS HERÓIS
# =====================================================
ACOES_HEROI = ["atacar", "defender", "item", "transformar", "contrato", "descansar", "fugir", "sair"]


def linha_efeitos(c):
    ativos = [f"{nome}({turnos})" for nome, turnos in c["efeitos"].items() if turnos > 0]
    return ", ".join(ativos) if ativos else "nenhum"


def descrever_ataque(nome):
    a = ATAQUES[nome]
    partes = []

    if a.get("util"):
        util = a["util"]

        if "clima" in util:
            partes.append(f"cria clima: {util['clima']}")
        if "protecao" in util:
            partes.append(f"barreira de {util['protecao']} por {util['rodadas']} rodadas")
        if "cura" in util:
            partes.append(f"cura {util['cura']}")
    else:
        partes.append(f"dano {a['dano']}")

    partes.append(f"energia {a['energia']}")

    if a.get("golpes"):
        partes.append(f"{a['golpes']} golpes")
    if a.get("area"):
        partes.append("atinge todos")
    if a.get("carrega"):
        partes.append(f"carrega {a['carrega']} turno(s)")
    if a.get("efeito"):
        partes.append(f"{a['efeito']} ({a.get('chance', 100)}%)")
    if a.get("elemento"):
        partes.append(a["elemento"])
    if a.get("requer"):
        partes.append(f"ESPECIAL: precisa de {a['requer']} ataques")

    return ", ".join(partes)


def mostrar_status(c):
    if clima["tipo"] != "limpo":
        print(f"\n[Clima: {CLIMAS[clima['tipo']]['nome']} — {clima['restam']} rodada(s)]")

    for i, inim in enumerate(vivos("inimigo"), 1):

        extras = []

        if inim["carregando"]:
            extras.append(f"CARREGANDO {inim['carregando']['ataque']} (dispara em {inim['carregando']['restam']})")
        if inim["forma_estado"]["ativa"]:
            extras.append(f"forma {inim['forma_estado']['atual']['nome']}")
        if inim["barreira"]["valor"] > 0:
            extras.append(f"barreira {inim['barreira']['valor']}")
        if inim["contrato"]:
            extras.append(inim["contrato"]["nome"])

        extras_txt = " | " + "; ".join(extras) if extras else ""

        print(
            f"  Inimigo {i}: {R(inim)} [{nome_elemento(elemento_defensivo(inim))}] "
            f"{inim['vida']}/{inim['vida_maxima']} de vida, "
            f"efeitos: {linha_efeitos(inim)}{extras_txt}"
        )
        print(f"      {texto_afinidades(inim)}")

    if len(herois) > 1:
        for aliado in vivos("heroi"):
            if aliado is not c:
                print(f"  Aliado: {aliado['nome']} ({aliado['chave']}) {aliado['vida']}/{aliado['vida_maxima']} de vida")

    print(
        f"{c['nome']} ({c['chave']}) [{nome_elemento(elemento_defensivo(c))}]: "
        f"vida {c['vida']}/{c['vida_maxima']}, "
        f"energia {c['energia']}/{c['energia_maxima']}, efeitos: {linha_efeitos(c)}"
    )

    if c["escudo_recarga"] > 0:
        print(f"Escudo: quebrado (volta em {c['escudo_recarga']} turno(s)).")
    else:
        print(f"Escudo: {c['escudo_vida']}/{c['escudo_max']}.")

    especiais = [n for n in ataques_do(c) if ATAQUES[n].get("requer")]

    if especiais:
        detalhes = ", ".join(f"{n} {c['contador']}/{ATAQUES[n]['requer']}" for n in especiais)
        print(f"Ataques feitos para os especiais: {detalhes}.")

    if c["reliquia"]:
        print(f"Relíquia: {c['reliquia']['nome']}.")

    if c["contrato"]:
        print(f"Contrato: {c['contrato']['nome']}.")

    if c["imunidade"] > 0:
        print(f"Imune por mais {c['imunidade']} rodada(s).")

    if c["barreira"]["valor"] > 0:
        print(f"Barreira: {c['barreira']['valor']}.")

    if c["forma_estado"]["ativa"]:
        print(f"Mega forma {c['forma_estado']['atual']['nome']} ({c['forma_estado']['restam']} turno(s) restantes).")

    for inim in vivos("inimigo"):
        carga = inim["carregando"]

        if carga:
            print(f"ATENÇÃO: {r(inim)} está carregando {carga['ataque']}!")

            if carga["restam"] == 1:
                print("Ele dispara no PRÓXIMO turno dele! Defenda, esquive ou impeça-o de agir (congelar/paralisar).")


def escolher_alvo(lista, rotulo):
    if len(lista) == 1:
        return lista[0]

    for i, c in enumerate(lista, 1):
        print(f"  {i} - {R(c)} ({c['vida']}/{c['vida_maxima']})")

    texto = input(f"Escolha o {rotulo} (número): ").strip()

    if texto.isdigit() and 1 <= int(texto) <= len(lista):
        return lista[int(texto) - 1]

    print("Escolha inválida.")
    return None


def escolher_aliado():
    return escolher_alvo(vivos("heroi"), "aliado")


def heroi_atacar(c):
    disponiveis = ataques_do(c)

    print("Seus ataques disponíveis:")

    for nome in disponiveis:
        print(f"  - {nome} ({descrever_ataque(nome)})")

    nome_ataque = achar_nome(input("Escolha o ataque que queira usar: "), disponiveis)

    if nome_ataque is None:
        print("Escolha um ataque correto!")
        return False

    ataque = ATAQUES[nome_ataque]

    if not ataque_disponivel(c, nome_ataque):
        print(
            f"{nome_ataque} é um ataque especial: precisa de {ataque['requer']} "
            f"ataques e você fez {c['contador']}."
        )
        return False

    if c["energia"] < ataque["energia"]:
        print(f"Você não possui energia suficiente para usar {nome_ataque}.")
        return False

    # ataques de utilidade (clima, proteção, cura)
    if ataque.get("util"):

        alvo_util = c

        if ("cura" in ataque["util"] or "protecao" in ataque["util"]) and len(vivos("heroi")) > 1:
            alvo_util = escolher_aliado()

            if alvo_util is None:
                return False

        c["energia"] -= ataque["energia"]
        registrar_uso(c, nome_ataque)
        print(f"{R(c)} usou {nome_ataque} e gastou {ataque['energia']} de energia.")
        usar_util(c, alvo_util, ataque)
        return True

    if ataque.get("area"):
        alvos = vivos("inimigo")
    else:
        alvo = escolher_alvo(vivos("inimigo"), "alvo")

        if alvo is None:
            return False

        alvos = [alvo]

    c["energia"] -= ataque["energia"]
    registrar_uso(c, nome_ataque)

    turnos_carga = int(ataque.get("carrega", 0) or (
        1 if (c.get("reliquia") or {}).get("nome") == "grande espada" and ataque.get("dano", 0) >= 35 else 0
    ))
    if turnos_carga:

        c["carregando"] = {"ataque": nome_ataque, "restam": turnos_carga, "alvos": alvos}

        print(
            f"{R(c)} gastou {ataque['energia']} de energia e começou a carregar "
            f"{nome_ataque}! Dispara em {turnos_carga} turno(s) dele."
        )
        return True

    print(f"{R(c)} usou {nome_ataque} e gastou {ataque['energia']} de energia.")
    usar_ataque(c, nome_ataque, alvos)
    return True


def heroi_defender(c):
    if c.get("restricoes_elixir") or c.get("restricoes_pingente"):
        print("Uma restrição ativa impede que você defenda.")
        return False
    if restringe(c, "defender"):
        print("Seu contrato impede que você se defenda. Escolha outra ação.")
        return False

    if c["escudo_max"] <= 0 or c["escudo_recarga"] > 0 or c["escudo_vida"] <= 0:
        print(
            f"O escudo de {r(c)} está quebrado e volta em "
            f"{c['escudo_recarga']} turno(s). Escolha outra ação."
        )
        return False

    c["defendendo"] = True

    print(
        f"{R(c)} levantou o escudo ({c['escudo_vida']}/{c['escudo_max']}). "
        f"Ele protege até o fim do próximo turno dos inimigos."
    )
    return True


def heroi_descansar(c):
    if restringe(c, "descansar"):
        print("Seu contrato impede que você descanse. Escolha outra ação.")
        return False

    c["energia"] = min(c["energia_maxima"], c["energia"] + DESCANSO["energia"])
    ganho = curar(c, c["vida_maxima"] * DESCANSO["vida_pct"])

    if c["escudo_recarga"] == 0 and c["escudo_max"] > 0:
        c["escudo_vida"] = min(c["escudo_max"], c["escudo_vida"] + DESCANSO["escudo"])

    print(
        f"{R(c)} descansou: energia {c['energia']}/{c['energia_maxima']}, "
        f"vida +{ganho}, escudo {c['escudo_vida']}/{c['escudo_max']}."
    )
    return True


def heroi_contrato(c):
    if c.get("restricoes_elixir"):
        print("O elixir da negação impede contratos.")
        return False
    if c["contrato"]:
        print("Você já fez um contrato nesta luta.")
        return False

    if c["forma_estado"]["usada"]:
        print("Quem já usou a mega forma não pode fazer contrato.")
        return False

    print("Contratos disponíveis (quem faz contrato não pode usar mega forma):")

    for nome, dados_contrato in CONTRATOS.items():
        print(f"  - {nome}: {dados_contrato['descricao']}")

    nome = achar_nome(input("Escolha o contrato (ou deixe vazio para cancelar): "), CONTRATOS)

    if nome is None:
        print("Contrato cancelado.")
        return False

    assinar_contrato(c, nome)
    return True


def heroi_transformar(c):
    if c.get("restricoes_elixir"):
        print("O elixir da negação impede a transformação.")
        return False
    fe = c["forma_estado"]

    if c["contrato"]:
        print("Quem fez um contrato não pode usar mega forma.")
        return False

    if not c["formas"]:
        print("Esta classe não possui mega forma.")
        return False

    if fe["usada"]:
        print("Você já usou sua mega forma nesta luta.")
        return False

    if c["energia"] < FORMAS["energia_heroi"]:
        print(f"Você precisa de {FORMAS['energia_heroi']} de energia para se transformar.")
        return False

    if len(c["formas"]) == 1:

        forma = c["formas"][0]

    else:

        opcoes = ", ".join(f"{f['letra']}: {f['nome']}" for f in c["formas"])

        for f in c["formas"]:
            print(
                f"  {f['letra']} - {f['nome']}: {f['descricao']} "
                f"| Habilidade {f['habilidade']['nome']}: {f['habilidade']['descricao']}"
            )

        texto = normalizar(input(f"Escolha a mega forma ({opcoes}): "))

        forma = None

        for f in c["formas"]:
            if texto == normalizar(f["letra"]):
                forma = f

        if forma is None:
            nome = achar_nome(texto, [f["nome"] for f in c["formas"]])

            for f in c["formas"]:
                if f["nome"] == nome:
                    forma = f

        if forma is None:
            print("Escolha uma forma correta!")
            return False

    c["energia"] -= FORMAS["energia_heroi"]
    ativar_forma(c, forma)
    return True


def aplicar_item(c, nome):
    if inventario[nome] <= 0:
        print("Você não possui mais esse item.")
        return False

    item = ITENS[nome]
    tipo = item["tipo"]
    if c.get("restricoes_pingente") and tipo in ("cura", "fumaca", "bomba", "pedra", "climatica"):
        print("O pingente da rejeição impede cura e consumíveis arremessáveis.")
        return False

    if tipo == "negacao":
        if c.get("elixir_nega_usado") or c["vida"] / max(1, c["vida_maxima"]) >= .20:
            print("O elixir da negação só funciona uma vez e abaixo de 20% da vida.")
            return False
        inventario[nome] -= 1
        c["vida"] = 1
        c["elixir_nega_usado"] = True
        c["restricoes_elixir"] = True
        print(f"{R(c)} negou a morte e permaneceu com 1 HP. Não poderá defender, contratar, curar, transformar ou fugir.")
        return True
    if tipo == "tipagem":
        c["elemento"] = {"chuva": "agua", "sol": "fogo", "neve": "gelo", "tempestade": "raio", "chuva_trovoada": "raio", "chuva_tempestade": "ar", "ventania": "ar"}.get(clima["tipo"], "neutro")
        inventario[nome] -= 1
        print(f"{R(c)} agora é do tipo {c['elemento']} por causa do clima.")
        return True
    if tipo == "maximizadora":
        inventario[nome] -= 1
        c["vida_maxima"] = round(c["vida_maxima"] * 1.5)
        c["vida"] = min(c["vida_maxima"], round(c["vida"] * 1.5))
        c["vida_maximizada_turnos"] = item.get("duracao", 3)
        print(f"A vida máxima de {R(c)} aumentou em 50% por {item['duracao']} turnos.")
        return True
    if tipo == "vulnerabilidade":
        alvo = escolher_alvo(vivos("inimigo"), "alvo")
        if alvo is None: return False
        if alvo.get("reliquia") and alvo["reliquia"].get("mods", {}).get("anti_controle"):
            print(f"{R(alvo)} anulou o item com o equipamento anti controle.")
            inventario[nome] -= 1
            return True
        alvo.setdefault("vulnerabilidades", {}).update({e: 1.25 for e in item["elementos"]})
        inventario[nome] -= 1
        print(f"{R(alvo)} ficou vulnerável a {', '.join(item['elementos'])}.")
        if (nome == "cruz sagrada" and c["elemento"] == "luz") or (nome == "correntes sombrias" and c["elemento"] in ("sombra", "fantasma")):
            c["dano_item_mult"] = c.get("dano_item_mult", 1) * 1.025
            c["velocidade"] = round(c["velocidade"] * 1.025)
            c["defesa"] = round(c["defesa"] * 1.025)
            c["energia_maxima"] = round(c["energia_maxima"] * 1.025)
            c["energia"] = min(c["energia_maxima"], round(c["energia"] * 1.025))
            print(f"{R(c)} recebeu +2,5% nos atributos contra seu elemento oposto.")
        return True

    if tipo == "cura":

        alvo = escolher_aliado()

        if alvo is None:
            return False

        inventario[nome] -= 1
        ganho = curar(alvo, item["cura"])
        print(f"{R(alvo)} foi curado em {ganho} e está com {alvo['vida']}/{alvo['vida_maxima']} de vida.")

    elif tipo == "energia":

        alvo = escolher_aliado()

        if alvo is None:
            return False

        inventario[nome] -= 1
        antes = alvo["energia"]
        alvo["energia"] = min(alvo["energia_maxima"], alvo["energia"] + item["energia"])
        print(f"{R(alvo)} recuperou {alvo['energia'] - antes} de energia ({alvo['energia']}/{alvo['energia_maxima']}).")

    elif tipo == "antidoto":

        alvo = escolher_aliado()

        if alvo is None:
            return False

        limpaveis = ["veneno", "queima", "sangramento"]

        if not any(alvo["efeitos"][e] > 0 for e in limpaveis):
            print(f"{R(alvo)} não está envenenado, queimado nem sangrando.")
            return False

        for e in limpaveis:
            alvo["efeitos"][e] = 0

        inventario[nome] -= 1
        print(f"O antídoto removeu veneno, queimadura e sangramento de {r(alvo)}!")

    elif tipo == "ressusitador":

        print("O ressusitador não pode ser usado agora: ele ativa sozinho quando um herói morrer.")
        return False

    elif tipo == "fumaca":
        if c.get("restricoes_elixir"):
            print("O elixir da negação impede consumíveis arremessáveis.")
            return False

        # o item é gasto ao usar, dando certo ou não
        inventario[nome] -= 1

        if random.randint(0, 10) >= 5:
            print("Você fugiu da luta usando a bomba de fumaça.")
            estado["resultado"] = "fuga"
        else:
            print("A bomba de fumaça foi gasta, mas a fuga falhou.")

    elif tipo in ("bomba", "pedra"):
        if c.get("restricoes_elixir"):
            print("O elixir da negação impede consumíveis arremessáveis.")
            return False

        if item.get("area"):
            alvos = vivos("inimigo")
        else:
            alvo = escolher_alvo(vivos("inimigo"), "alvo")

            if alvo is None:
                return False

            alvos = [alvo]

        inventario[nome] -= 1
        print(f"{R(c)} jogou {nome}!")

        for alvo in alvos:
            if nome == "bomba fragmentada" and elemento_defensivo(alvo) == "fantasma":
                print(f"{R(alvo)} é imune à bomba fragmentada.")
                continue

            if not dano_direto(alvo, item["dano"], item.get("elemento")):
                continue

            if alvo["vida"] > 0:
                if item.get("elemento") == "gas":
                    alvo.setdefault("vulnerabilidades", {}).update({"fogo": 1.5, "raio": 1.5, "eletrico": 1.5, "planta": 1.5})
                    print(f"{R(alvo)} está vulnerável a combinações elementais.")
                if sorteio(item.get("chance", 100)):
                    aplicar_efeito(alvo, item["aplica"], item["duracao"])
                else:
                    print(f"{R(alvo)} resistiu ao efeito.")

    elif tipo == "climatica":

        # a bomba depende do clima atual (sem clima, só causa dano)
        alvo = escolher_alvo(vivos("inimigo"), "alvo")

        if alvo is None:
            return False

        cfg = CLIMAS[clima["tipo"]]
        bomba = cfg["bomba"]

        inventario[nome] -= 1
        print(f"{R(c)} jogou a bomba climática! (clima atual: {cfg['nome']})")

        if dano_direto(alvo, bomba["dano"], bomba.get("elemento")):
            if alvo["vida"] > 0 and bomba.get("efeito"):
                aplicar_efeito(alvo, bomba["efeito"], bomba["duracao"])

    elif tipo in ("forca", "aleatorio"):

        alvo = escolher_aliado()

        if alvo is None:
            return False

        inventario[nome] -= 1
        alvo["buffs"][tipo] = item["duracao"] + 1   # o turno em que bebe não conta

        if tipo == "forca":
            print(f"{R(alvo)} ficou {item['multiplicador']}x mais forte por {item['duracao']} turno(s)!")
        else:
            print(f"Os ataques de {r(alvo)} vão aplicar um efeito aleatório por {item['duracao']} turno(s)!")

    elif tipo == "velocidade":

        alvo = escolher_aliado()

        if alvo is None:
            return False

        inventario[nome] -= 1
        alvo["velocidade"] += item["velocidade"]
        print(
            f"{R(alvo)} aumentou a velocidade para {alvo['velocidade']} "
            f"(esquiva {chance_esquiva_c(alvo):.0f}%)."
        )

    return True


def heroi_item(c, item_direto):
    if restringe(c, "itens"):
        print("Seu contrato impede o uso de itens. Escolha outra ação.")
        return False

    if item_direto is None:

        print("Itens disponíveis:")

        for nome, quantidade in inventario.items():
            print(f"  - {nome} (x{quantidade})")

        item_direto = achar_nome(input("Escolha o item a usar: "), inventario)

        if item_direto is None:
            print("Escolha o item certo!")
            return False

    return aplicar_item(c, item_direto)


def heroi_fugir(c):
    if c.get("restricoes_elixir") or c.get("restricoes_pingente"):
        print("Uma restrição ativa impede a fuga.")
        return False
    mais_rapido = max((e["velocidade"] for e in vivos("inimigo")), default=0)
    chance = 100 if c["velocidade"] > mais_rapido else max(0, min(95, 50 + (c["velocidade"] - mais_rapido) // 2))
    penalidade = sum(25 for e in ("lento", "aprisionado", "medo", "paralisado") if c["efeitos"].get(e, 0) > 0)
    penalidade += round((1 - c["vida"] / max(1, c["vida_maxima"])) * 45)
    if c["velocidade"] <= mais_rapido:
        chance = max(0, chance - penalidade)
    print(f"Chance de fuga: {chance}% (velocidade, condições e vida).")
    if random.randint(1, 100) <= chance:
        print("O grupo conseguiu fugir!")
        estado["resultado"] = "fuga"
    else:
        print("Vocês não conseguiram fugir.")

    return True


def acao_heroi(c):
    while True:

        mostrar_status(c)

        texto = input(
            f"[{c['nome']}] Escolha uma ação ({', '.join(ACOES_HEROI)}): "
        )

        item_direto = None
        acao = achar_nome(texto, ACOES_HEROI)

        if acao is None and normalizar(texto) in ("pocao", "itens"):
            acao = "item"

        # aceita também o nome de um item digitado direto como ação
        if acao is None:
            item_direto = achar_nome(texto, inventario)

            if item_direto is None:
                print("Escolha uma ação correta!")
                continue

            acao = "item"

        if acao == "atacar":
            gastou = heroi_atacar(c)
        elif acao == "defender":
            gastou = heroi_defender(c)
        elif acao == "item":
            gastou = heroi_item(c, item_direto)
        elif acao == "transformar":
            gastou = heroi_transformar(c)
        elif acao == "contrato":
            gastou = heroi_contrato(c)
        elif acao == "descansar":
            gastou = heroi_descansar(c)
        elif acao == "sair":
            estado["resultado"] = "saida"
            gastou = True
        else:
            gastou = heroi_fugir(c)

        if gastou or estado["resultado"]:
            return


# =====================================================
# FASES, RODADAS E FIM DA BATALHA
# =====================================================
def turno_combatente(c):
    if c["lado"] == "heroi":
        if len(herois) == 1:
            print("\n--- SEU TURNO ---")
        else:
            print(f"\n--- TURNO DE {c['nome'].upper()} ({c['chave']}) ---")
    else:
        print(f"\n--- TURNO DO INIMIGO: {R(c)} ---")

    pode_agir = inicio_de_turno(c)

    if c["vida"] <= 0 or c["fugiu"]:
        return

    if not pode_agir:

        # perder o turno interrompe o ataque que estava sendo carregado
        if c["carregando"]:
            print(f"A carga de {c['carregando']['ataque']} de {r(c)} foi interrompida!")
            c["carregando"] = None

    elif c["carregando"]:
        continuar_carga(c)

    elif c["lado"] == "heroi":
        acao_heroi(c)

    else:
        acao_inimigo(c)

    if c["vida"] > 0 and not c["fugiu"]:
        fim_de_turno(c)


def verificar_fim():
    if estado["resultado"]:
        return

    if not vivos("heroi"):
        estado["resultado"] = "derrota"

    elif not vivos("inimigo"):
        if any(e["morto"] for e in inimigos_lista):
            estado["resultado"] = "vitoria"
        else:
            estado["resultado"] = "fuga_inimigo"


def fase(lado):
    for c in sorted(vivos(lado), key=lambda x: -x["velocidade"]):

        if c["vida"] <= 0 or c["fugiu"] or c["morto"]:
            continue

        turno_combatente(c)
        verificar_fim()

        if estado["resultado"]:
            return

    if lado == "inimigo":

        # a fase dos inimigos acabou: escudos abaixam e a imunidade diminui
        for h in herois:
            h["defendendo"] = False

            if h["imunidade"] > 0:
                h["imunidade"] -= 1


def batalha():
    # quem tem o combatente mais rápido começa
    if max(h["velocidade"] for h in herois) > max(i["velocidade"] for i in inimigos_lista):
        lados = ["heroi", "inimigo"]
    else:
        lados = ["inimigo", "heroi"]

    rodada = 0

    while not estado["resultado"]:

        rodada += 1
        print(f"\n{'=' * 18} RODADA {rodada} {'=' * 18}")

        if rodada > 400:
            estado["resultado"] = "empate"
            break

        for lado in lados:
            fase(lado)

            if estado["resultado"]:
                break

        if estado["resultado"]:
            break

        fim_de_rodada()
        verificar_fim()


# =====================================================
# PREPARAÇÃO DA BATALHA
# =====================================================
def sortear_inimigos(quantidade):
    if INIMIGOS_FORCADOS:
        return list(INIMIGOS_FORCADOS)

    # todos os inimigos disponíveis entram no mesmo sorteio,
    # sem se importar com a classificação
    disponiveis = [nome for lista in DIFICULDADES.values() for nome in lista]

    sorteados = random.sample(disponiveis, min(quantidade, len(disponiveis)))

    # chance pequena de o inimigo secreto aparecer no lugar de um deles
    for i in range(len(sorteados)):
        if "gojo" not in sorteados and sorteio(CHANCE_SECRETO):
            sorteados[i] = "gojo"

    return sorteados


def configurar_batalha():
    herois.clear()
    inimigos_lista.clear()
    inventario.clear()
    estado["resultado"] = None
    terreno.update(nome="Campo comum", restam=0, criador=None)
    invocacao_estado["usada"] = False
    clima.update(tipo="limpo", restam=0)
    modo = perguntar("Modo de batalha (solo ou dupla): ", ["solo", "dupla"])
    quantidade = 1 if modo == "solo" else 2

    # nomes dos jogadores (na dupla são dois jogadores, cada um com o seu nome)
    nomes = []

    for i in range(quantidade):

        if quantidade == 1:
            texto = input("Digite o seu nome: ")
        else:
            texto = input(f"Digite o nome do jogador {i + 1}: ")

        texto = texto.strip() or f"Jogador {i + 1}"

        if texto in nomes:
            texto = f"{texto} {len(nomes) + 1}"

        nomes.append(texto)

    # classe e relíquia de cada jogador
    for nome_jogador in nomes:

        classe = perguntar(
            f"Escolha a classe de {nome_jogador} ({', '.join(CLASSES)}): ",
            list(CLASSES),
        )

        heroi = novo_combatente(classe, CLASSES[classe], "heroi", nome_jogador)

        print(f"Relíquias disponíveis para {nome_jogador}:")

        for nome_reliquia, dados_reliquia in RELIQUIAS.items():
            print(f"  - {nome_reliquia}: {dados_reliquia['descricao']}")

        escolha = perguntar(
            f"Escolha a relíquia de {nome_jogador} (ou 'nenhum'): ",
            ["nenhum"] + list(RELIQUIAS),
        )

        if escolha != "nenhum":
            equipar_reliquia(heroi, escolha, RELIQUIAS[escolha])

        herois.append(heroi)

    # inimigos (na dupla aparece mais um inimigo)
    for nome in sortear_inimigos(quantidade):

        inimigo = novo_combatente(nome, INIMIGOS[nome], "inimigo", nome)

        # relíquia de inimigo (o secreto não carrega)
        if nome != "gojo" and sorteio(CHANCE_RELIQUIA_INIMIGO):
            nome_reliquia = random.choice(list(RELIQUIAS_INIMIGO))
            equipar_reliquia(inimigo, nome_reliquia, RELIQUIAS_INIMIGO[nome_reliquia])

        inimigos_lista.append(inimigo)
        if nome == "gojo":
            print("Parabéns, você está ferrado: terá que enfrentar o Gojo de classe secreta!")

    multiplicador = INVENTARIO_DUPLA if quantidade == 2 else 1

    for nome, dados in ITENS.items():
        inventario[nome] = dados["quantidade"] * multiplicador

    # clima inicial (60% de chance de começar com algum clima)
    if random.random() < 0.6:
        definir_clima(
            random.choice([k for k in CLIMAS if k != "limpo"]),
            CLIMA_DURACAO + 1,
        )

    # Reliquias com ambiente permanente prevalecem sobre o clima inicial aleatorio.
    combatentes = herois + inimigos_lista
    if any((c.get("reliquia") or {}).get("mods", {}).get("terreno_infernal") for c in combatentes):
        definir_clima("sol", CLIMA_DURACAO)
        definir_terreno("Terreno magmático", 5)
    if any((c.get("reliquia") or {}).get("nome") == "amuleto da lua de sangue" for c in combatentes):
        definir_clima("lua_sangue", 999)

    print("\nJogadores:")

    for h in herois:
        print(
            f"  {h['nome']} ({h['chave']}, {nome_elemento(h['elemento'])}): "
            f"{h['vida']} de vida, {h['energia']} de energia."
        )
        print(f"    Habilidade: {h['habilidade']['nome']} — {h['habilidade']['descricao']}")

        if h["reliquia"]:
            print(f"    Relíquia: {h['reliquia']['nome']} — {h['reliquia']['descricao']}")

        for f in h["formas"]:
            letra = f"{f['letra']} - " if f.get("letra") else ""
            exclusivos = f" | ataques: {', '.join(f['ataques'])}" if f.get("ataques") else ""
            print(f"    Mega forma {letra}{f['nome']}: {f['descricao']}{exclusivos}")

    print("\nVocê terá que enfrentar:")

    for e in inimigos_lista:
        print(
            f"  {R(e)} ({nome_elemento(e['elemento'])}): {e['vida']} de vida, "
            f"{e['defesa']} de defesa, velocidade {e['velocidade']}."
        )
        print(f"    {texto_afinidades(e)}")
        print(f"    Habilidade: {e['habilidade']['nome']} — {e['habilidade']['descricao']}")

        if e["reliquia"]:
            print(f"    Relíquia: {e['reliquia']['nome']} — {e['reliquia']['descricao']}")

        if e["contratos"]:
            print(f"    Pode fazer: {', '.join(e['contratos'])}")

        for f in e["formas"]:
            letra = f"{f['letra']} - " if f.get("letra") else ""
            print(f"    Mega forma {letra}{f['nome']} (abaixo de {e['forma_vida_pct']}% de vida)")


def resultado_final():
    nomes = " e ".join(h["nome"] for h in herois)

    if len(herois) == 1:
        mensagens = {
            "vitoria": f"{nomes} venceu a batalha!",
            "derrota": f"{nomes} foi derrotado...",
            "fuga": f"{nomes} fugiu da batalha.",
        }
    else:
        mensagens = {
            "vitoria": f"{nomes} venceram a batalha!",
            "derrota": f"{nomes} foram derrotados...",
            "fuga": f"{nomes} fugiram da batalha.",
        }

    mensagens["fuga_inimigo"] = "Os inimigos fugiram. Vocês não os derrotaram."
    mensagens["empate"] = "A batalha durou demais e terminou empatada."
    mensagens["saida"] = "Você encerrou a partida."

    print(f"\n{mensagens[estado['resultado']]}")


def main():
    configurar_batalha()
    batalha()
    resultado_final()


if __name__ == "__main__":
    main()
