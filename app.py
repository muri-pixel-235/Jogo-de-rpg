"""Interface Pygame: menus, preparação, batalha e ferramentas de desenvolvimento."""
from __future__ import annotations

import json
import random
from pathlib import Path

import pygame

from batalha import (ATAQUES, CHANCE_SECRETO, CLASSES, CLIMAS, CONTRATOS, CONTRATOS_PERSONAGEM, DIFICULDADES, EFEITOS,
                     INIMIGOS, ITENS, RELIQUIAS, RELIQUIAS_INIMIGO)
from .engine import Battle, Fighter, make_enemy, make_player

WIDTH, HEIGHT = 1280, 760
ROOT = Path(__file__).resolve().parent.parent
BG = (14, 19, 31)
PANEL = (25, 34, 52)
PANEL2 = (33, 45, 67)
TEXT = (235, 241, 250)
MUTED = (151, 169, 191)
CYAN = (74, 211, 220)
GOLD = (255, 196, 91)
RED = (230, 93, 112)
GREEN = (93, 210, 145)
BLUE = (103, 155, 255)


class Button:
    def __init__(self, rect, label, action, *, fill=PANEL2, accent=CYAN, enabled=True):
        self.rect, self.label, self.action = pygame.Rect(rect), label, action
        self.fill, self.accent, self.enabled = fill, accent, enabled

    def draw(self, surface, font, mouse):
        hover = self.rect.collidepoint(mouse) and self.enabled
        color = tuple(min(255, c + (10 if hover else 0)) for c in self.fill)
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, self.accent if self.enabled else MUTED, self.rect, 2, border_radius=12)
        label = font.render(self.label, True, TEXT if self.enabled else MUTED)
        max_width = self.rect.width - 18
        if label.get_width() > max_width:
            label = pygame.transform.smoothscale(label, (max_width, label.get_height()))
        surface.blit(label, label.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


class RPGApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("RPG de Batalha — Pygame")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui", 18)
        self.small = pygame.font.SysFont("segoeui", 14)
        self.medium = pygame.font.SysFont("segoeui", 24, bold=True)
        self.large = pygame.font.SysFont("segoeui", 44, bold=True)
        self.running = True
        self.page = "home"
        self.buttons: list[Button] = []
        self.mode = "solo"
        self.team_size = 1
        self.turn_time_limit = 60
        self.turn_deadline_ms = 0
        self.timed_actor = None
        self.prepared_inventory: dict[str, int] = {}
        self.setup_step = 0
        self.setup_name = "Aventureiro"
        self.setup_class = "cavaleiro"
        self.setup_relic = "nenhum"
        self.opponent_name = "morcego"
        self.setup_focus = "player_name"
        self.setup_inputs = ["", "", "", "", "", "", "", ""]
        self.setup_player_classes = ["cavaleiro", "mago", "arqueiro", "velocista"]
        self.setup_player_enemies = ["morcego"] * 4
        self.setup_player_is_enemy = [False] * 4
        self.setup_foe_classes = ["morcego", "golem de gelo", "esqueleto guerreiro", "mestre mago"]
        self.setup_slot = 0
        self.rival_slots = ["cavaleiro", "mago", "arqueiro", "velocista"]
        self.rival_is_enemy = [False] * 4
        self.setup_relics = ["nenhum"] * 8
        self.enemy_scroll = 0
        self.class_scroll = 0
        self.relic_scroll = 0
        self.attack_page = 0
        self.item_page = 0
        self.battle: Battle | None = None
        self.dev_battle: Battle | None = None
        self.inventory: dict[str, int] = {}
        self.pending_attack: str | None = None
        self.pending_item: str | None = None
        self.pending_contract = False
        self.pending_transform = False
        self.selected_target: Fighter | None = None
        self.notice = ""
        self.notice_until = 0
        self.history_scroll = 0
        self.result_log_scroll = 0
        self.dev_input = ""
        self.dev_auth_stage: str | None = None
        self.dev_auth_input = ""
        self.dev_auth_reveal = False
        self.dev_waiting_confirmation: str | None = None
        self.dev_failing: list[str] = []
        self.dev_working: list[str] = []
        self.dev_dummy: Fighter | None = None
        self.setup_name_index = 0
        self.art_cache = {}
        self.art_scaled_cache = {}
        try:
            self.art_manifest = json.loads((ROOT / "pygame_rpg" / "assets" / "character_art.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.art_manifest = {"base": {}, "forms": {}}
        try:
            self.visual_assets = json.loads((ROOT / "pygame_rpg" / "assets" / "visual_assets.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.visual_assets = {}
        self.load_dev_results()

    def load_dev_results(self):
        path = ROOT / "dev_test_results.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.dev_working = payload.get("funcionando", [])
            self.dev_failing = payload.get("nao_funcionando", [])
        except (OSError, ValueError):
            pass

    def save_dev_results(self):
        path = ROOT / "dev_test_results.json"
        path.write_text(json.dumps({"funcionando": self.dev_working,
                                    "nao_funcionando": self.dev_failing},
                                   ensure_ascii=False, indent=2), encoding="utf-8")

    def notify(self, message: str):
        self.notice, self.notice_until = message, pygame.time.get_ticks() + 2600

    def text(self, value, x, y, color=TEXT, font=None):
        self.screen.blit((font or self.font).render(str(value), True, color), (x, y))

    def text_fit(self, value, x, y, width, color=TEXT, font=None, align="left"):
        font = font or self.font
        rendered = font.render(str(value), True, color)
        if rendered.get_width() > width:
            rendered = pygame.transform.smoothscale(rendered, (width, rendered.get_height()))
        if align == "center":
            x += (width - rendered.get_width()) // 2
        self.screen.blit(rendered, (x, y))

    def wrap(self, value: str, width: int, font=None) -> list[str]:
        font = font or self.font
        lines, current = [], ""
        for word in value.split():
            test = f"{current} {word}".strip()
            if font.size(test)[0] > width and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def paragraph(self, value: str, x: int, y: int, width: int, color=MUTED, font=None, limit=None):
        font = font or self.small
        lines = self.wrap(value, width, font)
        if limit:
            lines = lines[:limit]
        for i, line in enumerate(lines):
            self.text(line, x, y + i * (font.get_linesize() + 2), color, font)
        return y + len(lines) * (font.get_linesize() + 2)

    def panel(self, rect, title=None, accent=CYAN):
        r = pygame.Rect(rect)
        pygame.draw.rect(self.screen, PANEL, r, border_radius=18)
        pygame.draw.rect(self.screen, (50, 68, 94), r, 1, border_radius=18)
        if title:
            self.text(title, r.x + 18, r.y + 14, accent, self.medium)

    def add_button(self, rect, label, action, **kwargs):
        button = Button(rect, label, action, **kwargs)
        self.buttons.append(button)
        button.draw(self.screen, self.font, pygame.mouse.get_pos())

    def header(self, eyebrow, title, subtitle=""):
        self.text(eyebrow.upper(), 48, 26, CYAN, self.small)
        self.text_fit(title, 48, 48, self.screen.get_width() - 96, TEXT, self.large)
        if subtitle:
            self.text_fit(subtitle, 50, 106, self.screen.get_width() - 100, MUTED, self.font)

    def draw(self):
        self.screen.fill(BG)
        self.buttons = []
        if self.page == "home":
            self.draw_home()
        elif self.page == "settings":
            self.draw_settings()
        elif self.page == "setup":
            self.draw_setup()
        elif self.page == "backpack":
            self.draw_backpack()
        elif self.page == "barrel":
            self.draw_barrel()
        elif self.page == "battle":
            self.draw_battle()
        elif self.page == "briefing":
            self.draw_briefing()
        elif self.page == "results":
            self.draw_results()
        elif self.page == "dev":
            self.draw_dev()
        if self.notice and pygame.time.get_ticks() < self.notice_until:
            rect = pygame.Rect(340, HEIGHT - 60, WIDTH - 680, 42)
            pygame.draw.rect(self.screen, (46, 66, 84), rect, border_radius=12)
            self.screen.blit(self.font.render(self.notice, True, TEXT),
                             self.font.render(self.notice, True, TEXT).get_rect(center=rect.center))
        pygame.display.flip()

    def draw_home(self):
        # Fundo em camadas e brasão abstrato feito de formas vetoriais.
        pygame.draw.circle(self.screen, (24, 47, 67), (960, 265), 220)
        pygame.draw.circle(self.screen, (29, 65, 78), (960, 265), 160, 2)
        pygame.draw.polygon(self.screen, (41, 99, 111), [(960, 140), (1050, 220), (1020, 370), (960, 410), (900, 370), (870, 220)])
        pygame.draw.polygon(self.screen, (255, 206, 113), [(960, 184), (1007, 235), (990, 329), (960, 349), (930, 329), (913, 235)])
        self.text("ARENA  /  ELEMENTOS", 68, 85, CYAN, self.medium)
        self.text("RPG de", 64, 148, TEXT, self.large)
        self.text("Batalha", 64, 196, TEXT, self.large)
        self.paragraph("Monte seu grupo, escolha uma estratégia e enfrente batalhas por turnos em uma arena de fantasia.", 68, 267, 560, MUTED, self.font)
        self.add_button((68, 366, 250, 54), "Jogar", lambda: self.go_setup(), fill=(37, 94, 102))
        self.add_button((68, 432, 250, 48), "Configurações", lambda: self.go("settings"))
        self.add_button((68, 492, 250, 48), "Sair", lambda: setattr(self, "running", False), accent=RED)
        self.text("AVENTURA TÁTICA  •  TURNOS INDIVIDUAIS", 68, HEIGHT - 54, MUTED, self.small)
        self.text("P Y G A M E", 1086, HEIGHT - 54, CYAN, self.small)

    def draw_settings(self):
        self.header("Preferências", "Configurações", "Ajuste controles e acesse ferramentas de desenvolvimento.")
        self.panel((48, 168, 575, 430), "Jogo")
        self.paragraph("O protótipo usa desenho vetorial, resolução redimensionável e dados compartilhados com batalha.py.", 72, 226, 520)
        self.text("Resolução atual", 72, 306, TEXT)
        self.text(f"{self.screen.get_width()} × {self.screen.get_height()}", 72, 338, CYAN, self.medium)
        self.text("Controles", 72, 408, TEXT)
        self.paragraph("Mouse: escolher ações e alvos. Teclado: escrever nomes e comandos de teste.", 72, 440, 490)
        self.panel((650, 168, 582, 430), "Desenvolvimento", accent=GOLD)
        self.paragraph("Teste efeitos e terrenos contra um Dummy no ambiente de desenvolvimento.", 676, 226, 510)
        self.add_button((678, 346, 500, 54), "Abrir Dev Tools / Ambiente de Teste", self.begin_dev_auth, accent=GOLD)
        self.add_button((48, 640, 190, 48), "← Voltar", lambda: self.go("home"))
        if self.dev_auth_stage:
            pygame.draw.rect(self.screen, (0, 0, 0, 130), (0, 0, WIDTH, HEIGHT))
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((4, 8, 15, 190))
            self.screen.blit(veil, (0, 0))
            self.panel((350, 260, 580, 220), "Verificação de acesso", accent=GOLD)
            prompt = "Código de acesso" if self.dev_auth_stage == "code" else "Senha de confirmação"
            self.text(prompt + "  ·  pressione Enter", 380, 326, TEXT)
            shown = self.dev_auth_input if self.dev_auth_reveal else "•" * len(self.dev_auth_input)
            self.text(shown or "Digite o código", 380, 376, CYAN if shown else MUTED, self.medium)
            self.add_button((744, 366, 156, 42), "Ocultar" if self.dev_auth_reveal else "Mostrar",
                            lambda: setattr(self, "dev_auth_reveal", not self.dev_auth_reveal))

    def go_setup(self):
        self.mode = "solo"
        self.team_size = 1
        self.setup_slot = 0
        self.setup_step = 0
        self.setup_focus = ""
        self.go("setup")

    def begin_dev_auth(self):
        self.dev_auth_stage = "code"
        self.dev_auth_input = ""
        self.dev_auth_reveal = False

    def submit_dev_auth(self):
        if self.dev_auth_stage == "code" and self.dev_auth_input == "@dev.mode_true":
            self.dev_auth_stage = "password"
            self.dev_auth_input = ""
        elif self.dev_auth_stage == "password" and self.dev_auth_input == "@dev.mode_segurity123":
            self.dev_auth_stage = None
            self.dev_auth_input = ""
            self.dev_auth_reveal = False
            self.go("dev")
        else:
            self.dev_auth_stage = None
            self.dev_auth_input = ""
            self.dev_auth_reveal = False
            self.notify("Acesso negado.")

    def draw_setup(self):
        titles = {
            0: ("Preparação · etapa 1 de 4", "Escolha o modo de jogo", "Defina o formato da batalha e o tempo de cada turno."),
            1: ("Preparação · etapa 2 de 4", "Nome e personagem", "Digite os nomes e selecione uma classe ou personagem para cada participante."),
            2: ("Preparação · etapa 3 de 4", "Escolha as relíquias", "Selecione uma relíquia para cada participante."),
            3: ("Preparação · etapa 4 de 4", "Prepare a mochila", "Escolha até 10 tipos de consumível. A mochila fica travada durante a partida."),
        }
        eyebrow, title, subtitle = titles.get(self.setup_step, titles[0])
        self.header(eyebrow, title, subtitle)
        if self.setup_step == 0:
            self.draw_setup_mode()
        elif self.setup_step == 1:
            self.draw_setup_characters()
        elif self.setup_step == 2:
            self.draw_setup_relics()
        else:
            self.draw_setup_bag()

    def draw_setup_mode(self):
        self.panel((48, 160, 1184, 516), "Modo de jogo", accent=CYAN)
        modes = (("solo", "Solo", "1 jogador contra 1 inimigo"),
                 ("dupla", "Dupla", "2 jogadores contra 2 bots"),
                 ("bots", "Grupo vs bots", "Escolha equipes de 2 a 4 contra bots"),
                 ("multiplayer", "Multiplayer local", "Configure manualmente os dois lados"))
        for i, (mode, label, description) in enumerate(modes):
            x = 68 + i * 294
            card = pygame.Rect(x, 242, 270, 150)
            selected = self.mode == mode
            pygame.draw.rect(self.screen, (75, 65, 43) if selected else PANEL2, card, border_radius=12)
            pygame.draw.rect(self.screen, CYAN if selected else (57, 74, 96), card, 2 if selected else 1, border_radius=12)
            self.draw_mode_icon((card.centerx, card.y + 48), mode)
            self.text_fit(label, card.x + 18, card.y + 78, card.w - 36,
                          CYAN if selected else TEXT, self.medium, align="center")
            description_lines = self.wrap(description, card.w - 36, self.small)[:2]
            for line_index, line in enumerate(description_lines):
                self.text_fit(line, card.x + 18, card.y + 112 + line_index * 18,
                              card.w - 36, MUTED, self.small, align="center")
            self.buttons.append(Button(card, "", lambda m=mode: self.select_mode(m), fill=PANEL2, accent=CYAN))
        self.text("Tamanho das equipes", 82, 438, TEXT, self.font)
        for count in range(1, 5):
            self.add_button((82 + (count - 1) * 82, 478, 68, 48), str(count),
                            lambda n=count: self.set_team_size(n),
                            fill=(37, 94, 102) if count == self.team_size else PANEL2,
                            enabled=self.mode == "multiplayer" or (self.mode == "bots" and count >= 2))
        self.text("Tempo por turno", 600, 438, TEXT, self.font)
        for i, seconds in enumerate((30, 60, 90)):
            self.add_button((600 + i * 104, 478, 90, 48), f"{seconds} s",
                            lambda value=seconds: setattr(self, "turn_time_limit", value),
                            fill=(37, 94, 102) if seconds == self.turn_time_limit else PANEL2)
        note = "Grupo vs bots permite 2v2, 3v3 e 4v4. Multiplayer local configura os dois lados neste computador."
        self.paragraph(note, 82, 550, 920, MUTED, self.small)
        self.add_button((48, 700, 170, 42), "Menu", lambda: self.go("home"))
        self.add_button((972, 700, 230, 42), "Continuar →", self.advance_setup_step)

    def draw_mode_icon(self, center, mode):
        x, y = center
        accent = GOLD if self.mode == mode else CYAN
        count = {"solo": 1, "dupla": 2, "bots": min(4, self.team_size), "multiplayer": 3}.get(mode, 1)
        spacing = 22
        start_x = x - (count - 1) * spacing // 2
        for index in range(count):
            px = start_x + index * spacing
            pygame.draw.circle(self.screen, accent, (px, y - 12), 7)
            pygame.draw.rect(self.screen, accent, (px - 7, y - 3, 14, 24), border_radius=6)

    def setup_count(self):
        if self.mode == "multiplayer":
            return self.team_size * 2
        if self.mode == "bots":
            return self.team_size
        return 2 if self.mode == "dupla" else 1

    def setup_slot_details(self):
        rival = self.mode == "multiplayer" and self.setup_slot >= self.team_size
        side_index = self.setup_slot - self.team_size if rival else self.setup_slot
        name_index = 4 + side_index if rival else side_index
        relic_index = 4 + side_index if rival else side_index
        return rival, side_index, name_index, relic_index

    def draw_setup_characters(self):
        count = self.setup_count()
        self.setup_slot = max(0, min(count - 1, self.setup_slot))
        rival, side_index, name_index, _ = self.setup_slot_details()
        self.setup_name_index = name_index
        accent = RED if rival else BLUE
        self.panel((48, 160, 1184, 516), "Equipe B" if rival else "Equipe A", accent=accent)
        self.text(f"Participante {self.setup_slot + 1} de {count}", 78, 202, GOLD, self.medium)
        self.input_box((78, 260, 360, 46), "Nome (clique e digite)", self.setup_inputs[name_index],
                       "player_name", hint="Digite seu próprio nome")
        is_enemy = self.rival_is_enemy[side_index] if rival else self.setup_player_is_enemy[side_index]
        if self.mode == "multiplayer":
            self.add_button((470, 260, 172, 46), "Classe", lambda: self.set_side_type(side_index, rival, False),
                            fill=PANEL2 if not is_enemy else PANEL)
            self.add_button((650, 260, 220, 46), "Personagem inimigo", lambda: self.set_side_type(side_index, rival, True),
                            fill=(111, 47, 64) if is_enemy else PANEL, accent=RED)
        names = list(INIMIGOS) if is_enemy else list(CLASSES)
        page_size = 8
        page_attr = "enemy_scroll" if is_enemy else "class_scroll"
        page = getattr(self, page_attr)
        pages = max(1, (len(names) + page_size - 1) // page_size)
        page = min(page, pages - 1)
        setattr(self, page_attr, page)
        visible = names[page * page_size:(page + 1) * page_size]
        selected = (self.rival_slots[side_index] if rival else
                    self.setup_player_enemies[side_index] if is_enemy else
                    self.setup_player_classes[side_index])
        self.text("PERSONAGENS INIMIGOS" if is_enemy else "CLASSES", 78, 318, accent, self.small)
        for i, name in enumerate(visible):
            col, row = i % 4, i // 4
            data = INIMIGOS[name] if is_enemy else CLASSES[name]
            if is_enemy:
                detail = (f"HP {data.get('vida', 0)} · DEF {data.get('defesa', 0)} · EN {data.get('energia', 0)}\n"
                          f"VEL {data.get('velocidade', 0)} · {data.get('elemento', 'neutro')}")
            else:
                detail = (f"HP {data.get('vida', 0)} · DEF {data.get('defesa', 0)} · ESC {data.get('escudo', 0)}\n"
                          f"EN {data.get('energia', 0)} · VEL {data.get('velocidade', 0)}\n"
                          f"{data.get('funcao', 'DPS')} · dificuldade {data.get('dificuldade', 'Média')} · {data.get('habilidade', {}).get('nome', '—')}")
            action = lambda n=name: self.select_side_character(side_index, n, rival, is_enemy)
            category = "enemy" if is_enemy else "class"
            self.choice_card((78 + col * 282, 344 + row * 148, 270, 126), name, detail,
                             selected == name, action, RED if is_enemy else BLUE,
                             image=self.get_character_art(category, name))
        self.add_button((78, 640, 94, 28), "← Página", lambda: self.scroll_character_page(is_enemy, -1), enabled=page > 0)
        self.text(f"Página {page + 1}/{pages} · {len(names)} opções", 182, 647, MUTED, self.small)
        self.add_button((350, 640, 94, 28), "Página →", lambda: self.scroll_character_page(is_enemy, 1), enabled=page + 1 < pages)
        if count > 1:
            self.add_button((600, 638, 116, 30), "← Anterior", lambda: self.change_slot(-1), enabled=self.setup_slot > 0)
            self.add_button((728, 638, 116, 30), "Próximo →", lambda: self.change_slot(1), enabled=self.setup_slot + 1 < count)
        self.add_button((48, 700, 170, 42), "← Modo", lambda: self.set_setup_step(0))
        self.add_button((972, 700, 230, 42), "Escolher relíquias →", self.advance_setup_step)

    def draw_setup_relics(self):
        count = self.setup_count()
        self.setup_slot = max(0, min(count - 1, self.setup_slot))
        rival, side_index, name_index, relic_index = self.setup_slot_details()
        is_enemy = self.rival_is_enemy[side_index] if rival else self.setup_player_is_enemy[side_index]
        options = ["nenhum", *(RELIQUIAS_INIMIGO if is_enemy else RELIQUIAS)]
        selected_character = (self.rival_slots[side_index] if rival else
                              self.setup_player_enemies[side_index] if is_enemy else
                              self.setup_player_classes[side_index])
        participant_name = self.setup_inputs[name_index].strip() or f"Participante {self.setup_slot + 1}"
        self.panel((48, 160, 1184, 516), f"Relíquias · {participant_name} · {selected_character}", accent=RED if rival else BLUE)
        page_size = 12
        pages = max(1, (len(options) + page_size - 1) // page_size)
        self.relic_scroll = min(self.relic_scroll, pages - 1)
        visible = options[self.relic_scroll * page_size:(self.relic_scroll + 1) * page_size]
        self.text("Escolha uma relíquia", 78, 214, GOLD, self.medium)
        self.text("A descrição mostra o efeito da relíquia.", 78, 246, MUTED, self.small)
        selected = self.setup_relics[relic_index]
        for i, name in enumerate(visible):
            col, row = i % 4, i // 4
            data = (RELIQUIAS_INIMIGO if is_enemy else RELIQUIAS).get(name, {})
            description = data.get("descricao", "Sem bônus equipado.")
            self.choice_card((78 + col * 278, 280 + row * 100, 260, 88), name, description,
                             selected == name, lambda n=name: self.select_setup_relic(relic_index, n), GOLD,
                             image=self.get_visual_art("relics", name))
        self.add_button((78, 602, 94, 34), "← Página", lambda: self.scroll_relics(-1), enabled=self.relic_scroll > 0)
        self.text(f"Página {self.relic_scroll + 1}/{pages} · {len(options)} opções", 182, 610, MUTED, self.small)
        self.add_button((350, 602, 94, 34), "Página →", lambda: self.scroll_relics(1), enabled=self.relic_scroll + 1 < pages)
        if count > 1:
            self.add_button((600, 602, 116, 38), "← Anterior", lambda: self.change_slot(-1), enabled=self.setup_slot > 0)
            self.add_button((728, 602, 116, 38), "Próximo →", lambda: self.change_slot(1), enabled=self.setup_slot + 1 < count)
        self.add_button((48, 700, 170, 42), "← Personagem", lambda: self.set_setup_step(1))
        final_slot = self.setup_slot + 1 >= count
        self.add_button((972, 700, 230, 42), "Conferir batalha →" if final_slot else "Próximo participante →",
                        self.next_setup)

    def scroll_character_page(self, is_enemy, direction):
        attribute = "enemy_scroll" if is_enemy else "class_scroll"
        names = INIMIGOS if is_enemy else CLASSES
        page_size = 8
        pages = max(1, (len(names) + page_size - 1) // page_size)
        setattr(self, attribute, max(0, min(pages - 1, getattr(self, attribute) + direction)))

    def advance_setup_step(self):
        self.setup_focus = ""
        if self.setup_step == 1:
            self.setup_slot = 0
            self.relic_scroll = 0
        self.setup_step = min(2, self.setup_step + 1)

    def set_setup_step(self, step):
        self.setup_focus = ""
        self.setup_step = max(0, min(2, step))
    def choice_card(self, rect, title, description, selected, action, accent, image=None, enabled=True):
        card = pygame.Rect(rect)
        fill = (43, 74, 89) if selected and accent == BLUE else (91, 55, 67) if selected and accent == RED else (75, 65, 43) if selected else PANEL2
        if not enabled:
            fill = PANEL
        pygame.draw.rect(self.screen, fill, card, border_radius=10)
        pygame.draw.rect(self.screen, accent if selected else (57, 74, 96), card, 2 if selected else 1, border_radius=10)
        text_x, text_width = card.x + 10, card.w - 20
        if image:
            art_size = min(100, card.h - 12) if card.h >= 120 else min(48, card.h - 12)
            art_rect = pygame.Rect(card.x + 7, card.y + 6, art_size, card.h - 12)
            pygame.draw.rect(self.screen, (9, 13, 21), art_rect, border_radius=6)
            self.blit_art(image, art_rect)
            text_x = art_rect.right + (11 if card.h >= 120 else 8)
            text_width = card.right - text_x - (10 if card.h >= 120 else 8)
        title_color = (accent if selected else TEXT) if enabled else MUTED
        title_font = self.font if card.h >= 120 else self.small
        self.text_fit(title, text_x, card.y + 9, text_width, title_color, title_font)
        detail_lines = []
        for source_line in description.splitlines():
            if image and card.h <= 70:
                detail_lines.append(source_line)
            else:
                detail_lines.extend(self.wrap(source_line, text_width, self.small))
        y = card.y + (36 if card.h >= 120 else 26)
        max_lines = 5 if card.h >= 120 else 1 if card.h <= 56 else 4 if card.h > 100 else 2
        for line in detail_lines[:max_lines]:
            self.text_fit(line, text_x, y, text_width, MUTED if enabled else (104, 117, 136), self.small)
            y += 17 if card.h >= 120 else 16
        self.buttons.append(Button(card, "", action, fill=(0, 0, 0), accent=(0, 0, 0), enabled=enabled))

    def get_character_art(self, category, character, form=None):
        """Load a bundled illustration, falling back to the character's base art."""
        filename = None
        if form:
            filename = self.art_manifest.get("forms", {}).get(category, {}).get(character, {}).get(form)
        if not filename:
            filename = self.art_manifest.get("base", {}).get(category, {}).get(character)
        if not filename:
            return None
        if filename not in self.art_cache:
            path = ROOT / "pygame_rpg" / "assets" / filename
            if not path.exists():
                path = ROOT / "pygame_rpg" / "assets" / "characters" / filename
            try:
                self.art_cache[filename] = pygame.image.load(str(path)).convert_alpha()
            except (OSError, pygame.error):
                self.art_cache[filename] = None
        return self.art_cache[filename]

    def get_visual_art(self, category, name):
        filename = self.visual_assets.get(category, {}).get(name)
        if not filename:
            return None
        cache_key = f"visual:{filename}"
        if cache_key not in self.art_cache:
            path = ROOT / "pygame_rpg" / "assets" / filename
            try:
                self.art_cache[cache_key] = pygame.image.load(str(path)).convert_alpha()
            except (OSError, pygame.error):
                self.art_cache[cache_key] = None
        return self.art_cache[cache_key]

    def blit_art(self, image, rect, *, flip=False):
        if image is None:
            return
        rect = pygame.Rect(rect)
        scale = min(rect.width / image.get_width(), rect.height / image.get_height())
        size = (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
        key = (id(image), size, flip)
        rendered = self.art_scaled_cache.get(key)
        if rendered is None:
            rendered = pygame.transform.smoothscale(image, size)
            if flip:
                rendered = pygame.transform.flip(rendered, True, False)
            self.art_scaled_cache[key] = rendered
        self.screen.blit(rendered, rendered.get_rect(center=rect.center))

    def select_setup_slot(self, index):
        self.setup_slot = index
        if self.mode == "multiplayer" and index >= self.team_size:
            self.setup_name_index = 4 + index - self.team_size
        else:
            self.setup_name_index = index
        self.setup_focus = "player_name"

    def select_side_character(self, side_index, name, is_rival, is_enemy):
        if is_rival:
            self.rival_slots[side_index] = name
        elif is_enemy:
            self.setup_player_enemies[side_index] = name
        else:
            self.setup_player_classes[side_index] = name

    def set_side_type(self, side_index, is_rival, is_enemy):
        if is_rival:
            self.set_rival_type(side_index, is_enemy)
        else:
            self.setup_player_is_enemy[side_index] = is_enemy
            if is_enemy and self.setup_player_enemies[side_index] not in INIMIGOS:
                self.setup_player_enemies[side_index] = next(iter(INIMIGOS))

    def select_setup_relic(self, index, name):
        self.setup_relics[index] = name
        if index == 0:
            self.setup_relic = name
        if not self.setup_player_has_mask():
            self.prepared_inventory.pop("alma", None)

    def setup_player_has_mask(self):
        count = self.team_size if self.mode in ("bots", "multiplayer") else 2 if self.mode == "dupla" else 1
        return any(self.setup_relics[index] == "máscara de esqueleto" for index in range(count))

    def set_rival_type(self, side_index, is_enemy):
        self.rival_is_enemy[side_index] = is_enemy
        if is_enemy and self.rival_slots[side_index] not in INIMIGOS:
            self.rival_slots[side_index] = next(iter(INIMIGOS))
        elif not is_enemy and self.rival_slots[side_index] not in CLASSES:
            self.rival_slots[side_index] = next(iter(CLASSES))

    def scroll_enemies(self, direction):
        self.enemy_scroll = max(0, self.enemy_scroll + direction)

    def scroll_classes(self, direction):
        self.class_scroll = max(0, self.class_scroll + direction)

    def scroll_relics(self, direction):
        self.relic_scroll = max(0, self.relic_scroll + direction)

    def start_setup_battle(self):
        self.setup_slot = self.team_size * 2 - 1
        self.next_setup()

    def input_box(self, rect, label, value, focus, hint=""):
        self.text(label, rect[0], rect[1] - 22, MUTED, self.small)
        r = pygame.Rect(rect)
        active = self.setup_focus == focus
        pygame.draw.rect(self.screen, (20, 29, 44), r, border_radius=9)
        pygame.draw.rect(self.screen, CYAN if active else (58, 74, 96), r, 1, border_radius=9)
        shown = value or hint
        self.text(shown, r.x + 14, r.y + 12, TEXT if value else MUTED)
        self.buttons.append(Button(r, "", lambda: self.set_input_focus(focus), fill=(0, 0, 0), accent=(0, 0, 0)))

    def set_input_focus(self, focus):
        self.setup_focus = focus
        if focus == "player_name":
            pygame.key.start_text_input()

    def select_mode(self, mode):
        self.mode = mode
        self.setup_slot = 0
        self.team_size = {"solo": 1, "dupla": 2, "bots": max(2, self.team_size)}.get(mode, self.team_size)
        self.setup_step = 0

    def set_team_size(self, size):
        self.team_size, self.setup_slot = size, 0

    def change_slot(self, amount):
        count = self.setup_count()
        self.setup_slot = max(0, min(count - 1, self.setup_slot + amount))

    def cycle_setup_class(self, amount):
        options = list(CLASSES)
        if self.mode == "multiplayer" and self.setup_slot >= self.team_size:
            side_index = self.setup_slot - self.team_size
            if self.rival_is_enemy[side_index]:
                options = list(INIMIGOS)
                cur = self.rival_slots[side_index]
                self.rival_slots[side_index] = options[(options.index(cur) + amount) % len(options)] if cur in options else options[0]
            else:
                cur = self.rival_slots[side_index]
                self.rival_slots[side_index] = options[(options.index(cur) + amount) % len(options)]
            return
        cur = self.setup_player_classes[self.setup_slot]
        self.setup_player_classes[self.setup_slot] = options[(options.index(cur) + amount) % len(options)]

    def toggle_rival_type(self):
        slot = self.setup_slot
        if self.mode != "multiplayer" or slot < self.team_size:
            return
        side_index = slot - self.team_size
        self.rival_is_enemy[side_index] = not self.rival_is_enemy[side_index]
        self.rival_slots[side_index] = "morcego" if self.rival_is_enemy[side_index] else "cavaleiro"

    def cycle_relic(self):
        options = ["nenhum", *RELIQUIAS]
        self.setup_relic = options[(options.index(self.setup_relic) + 1) % len(options)]

    def next_setup(self):
        if self.setup_step == 3:
            self.page = "briefing"
            return
        count = self.setup_count()
        if self.setup_slot + 1 < count:
            self.change_slot(1)
            self.relic_scroll = 0
            return
        players = []
        enemies = []
        if self.mode == "multiplayer":
            for i in range(self.team_size):
                player_name = self.setup_inputs[i].strip() or f"Jogador {i + 1}"
                if self.setup_player_is_enemy[i]:
                    player_kind = self.setup_player_enemies[i]
                    players.append(Fighter.create(player_name, "player", player_kind,
                                                  INIMIGOS[player_kind], self.setup_relics[i]))
                else:
                    players.append(make_player(player_name, self.setup_player_classes[i], self.setup_relics[i]))
                rival_slot = i + 4
                name = self.setup_inputs[rival_slot].strip() or f"Rival {i + 1}"
                if self.rival_is_enemy[i]:
                    source = INIMIGOS[self.rival_slots[i]]
                    enemies.append(Fighter.create(name, "rival", self.rival_slots[i], source, self.setup_relics[rival_slot]))
                else:
                    source = CLASSES[self.rival_slots[i]]
                    enemies.append(Fighter.create(name, "rival", self.rival_slots[i], source, self.setup_relics[rival_slot]))
        else:
            player_count = self.team_size if self.mode == "bots" else 1 if self.mode == "solo" else 2
            for i in range(player_count):
                name = self.setup_inputs[i].strip() or f"Jogador {i + 1}"
                players.append(make_player(name, self.setup_player_classes[i], self.setup_relics[i]))
            pool = [name for names in DIFICULDADES.values() for name in names]
            for i in range(player_count):
                name = random.choice(pool)
                if name != "gojo" and random.random() < CHANCE_SECRETO / 100:
                    name = "gojo"
                enemies.append(make_enemy(name))
        self.battle = Battle(players, enemies, self.mode)
        self.battle.turn_time_limit = self.turn_time_limit
        base_count = self.team_size if self.mode == "bots" else 2 if self.mode == "dupla" else 1
        available = {name: data.get("quantidade", 0) * base_count for name, data in ITENS.items()}
        self.prepared_inventory = {name: min(amount, available.get(name, 0))
                                   for name, amount in self.prepared_inventory.items()
                                   if amount > 0 and name in available}
        if not self.prepared_inventory:
            self.prepared_inventory = dict(list(
                {name: amount for name, amount in available.items() if amount > 0}.items()
            )[:10])
        self.inventory = dict(self.prepared_inventory)
        self.battle.inventory = self.inventory
        self.pending_attack = self.pending_item = None
        self.pending_contract = False
        self.history_scroll = 0
        self.result_log_scroll = 0
        self.setup_step = 3
        self.item_page = 0
        self.page = "setup"

    def draw_setup_bag(self):
        if self.battle is None:
            self.draw_setup_relics()
            return
        self.panel((28, 154, 1224, 508), "Consumíveis · até 10 tipos", accent=GOLD)
        if not self.setup_player_has_mask():
            self.prepared_inventory.pop("alma", None)
        selected_types = sum(1 for amount in self.prepared_inventory.values() if amount > 0)
        self.text_fit(f"Tipos escolhidos: {selected_types}/10 · Um clique adiciona o pacote completo; outro remove.",
                      46, 190, 1160, MUTED, self.small)
        names = [name for name in ITENS if name != "alma" or self.setup_player_has_mask()]
        per_page = 20
        pages = max(1, (len(names) + per_page - 1) // per_page)
        self.item_page = min(self.item_page, pages - 1)
        visible = names[self.item_page * per_page:(self.item_page + 1) * per_page]
        for index, name in enumerate(visible):
            col, row = index % 4, index // 4
            x, y = 42 + col * 300, 218 + row * 82
            amount = self.prepared_inventory.get(name, 0)
            bag_multiplier = self.team_size if self.mode == "bots" else 2 if self.mode == "dupla" else 1
            max_amount = ITENS[name].get("quantidade", 0) * bag_multiplier
            detail = ITENS[name].get("descricao", "Consumível sem descrição.")
            self.choice_card((x, y, 282, 68), f"{name}  ×{amount}", detail, amount > 0,
                             lambda n=name, cap=max_amount: self.cycle_prepared_item(n, cap), GOLD,
                             image=self.get_visual_art("items", name),
                             enabled=amount > 0 or selected_types < 10)
        self.add_button((42, 696, 190, 42), "← Relíquias", lambda: self.set_setup_step(2))
        if pages > 1:
            self.add_button((734, 696, 104, 42), "Anterior", lambda: self.scroll_items(-1), enabled=self.item_page > 0)
            self.text_fit(f"Página {self.item_page + 1}/{pages}", 844, 710, 90, MUTED, self.small, align="center")
            self.add_button((940, 696, 104, 42), "Próxima →", lambda: self.scroll_items(1), enabled=self.item_page + 1 < pages)
        self.add_button((1060, 696, 192, 42), "Conferir batalha →", self.next_setup)

    def cycle_prepared_item(self, name, cap):
        current = self.prepared_inventory.get(name, 0)
        if current == 0:
            if sum(value > 0 for value in self.prepared_inventory.values()) >= 10:
                self.notify("A mochila aceita no máximo 10 tipos de item.")
                return
            self.prepared_inventory[name] = cap
        else:
            self.prepared_inventory.pop(name, None)

    def draw_briefing(self):
        if not self.battle:
            self.go("setup")
            return
        battle = self.battle
        self.header("Antes do combate", "Preparação da batalha", "Confira equipes, clima, terreno e a ordem de ação inicial.")
        self.panel((48, 168, 550, 408), "Equipe A", accent=BLUE)
        self.panel((682, 168, 550, 408), "Equipe B", accent=RED)
        for team, panel_x in ((battle.players, 48), (battle.enemies, 682)):
            if not team:
                continue
            columns = 1 if len(team) == 1 else 2
            rows = (len(team) + columns - 1) // columns
            content_x, content_y = panel_x + 16, 218
            content_width, content_height = 518, 344
            gap_x, gap_y = 10, 8
            cell_width = (content_width - gap_x * (columns - 1)) / columns
            cell_height = (content_height - gap_y * (rows - 1)) / rows
            portrait_size = 172 if len(team) == 1 else 116 if len(team) == 2 else 82
            for index, fighter in enumerate(team):
                col, row = index % columns, index // columns
                cell_x = round(content_x + col * (cell_width + gap_x))
                cell_y = round(content_y + row * (cell_height + gap_y))
                card = pygame.Rect(cell_x, cell_y, round(cell_width), round(cell_height))
                pygame.draw.rect(self.screen, (25, 36, 53), card, border_radius=10)
                pygame.draw.rect(self.screen, (48, 64, 86), card, 1, border_radius=10)

                art_category = "enemy" if fighter.kind in INIMIGOS else "class"
                art = self.get_character_art(art_category, fighter.kind, fighter.form)
                art_rect = pygame.Rect(0, 0, portrait_size, portrait_size)
                art_rect.centerx = card.centerx
                art_rect.y = card.y + 8
                pygame.draw.rect(self.screen, (9, 13, 21), art_rect, border_radius=8)
                if art:
                    self.blit_art(art, art_rect)
                else:
                    pygame.draw.rect(self.screen, (57, 74, 96), art_rect, 2, border_radius=8)

                heading_y = art_rect.bottom + (5 if len(team) <= 2 else 3)
                title_font = self.medium if len(team) <= 2 else self.small
                self.text_fit(self.fighter_heading(fighter), card.x + 8, heading_y,
                              card.w - 16, TEXT, title_font, align="center")
                defense = fighter.data.get("defesa", 0) + fighter.data.get("defesa_buff", 0)
                first_stats = f"HP {fighter.hp}/{fighter.max_hp}  ·  DEF {defense}  ·  ESC {fighter.shield}/{fighter.max_shield}"
                second_stats = f"EN {fighter.energy}/{fighter.max_energy}  ·  VEL {fighter.speed}  ·  {fighter.element}"
                # O título usa uma fonte de 24 px; separar as estatísticas evita
                # que elas encostem no nome nas cartas de preparação.
                stats_y = heading_y + (34 if len(team) <= 2 else 22)
                self.text_fit(first_stats, card.x + 6, stats_y, card.w - 12, MUTED, self.small, align="center")
                self.text_fit(second_stats, card.x + 6, stats_y + 18, card.w - 12, MUTED, self.small, align="center")
        self.panel((48, 590, 1184, 92), "Condições", accent=GOLD)
        self.text_fit(f"Clima: {CLIMAS[battle.weather]['nome']}   ·   Terreno: {battle.terrain}", 72, 636, 1010, TEXT)
        order = "  →  ".join(self.fighter_heading(f) for f in battle.turn_order)
        self.text_fit("Ordem: " + order, 72, 660, 1010, CYAN, self.small)
        terrain_art = self.get_visual_art("terrain", battle.terrain)
        if terrain_art:
            self.blit_art(terrain_art, pygame.Rect(1138, 601, 78, 68))
        self.add_button((1000, 704, 232, 44), "Começar batalha", self.start_battle, fill=(37, 94, 102))
        self.add_button((48, 704, 190, 44), "Voltar à preparação", lambda: self.go("setup"))

    def start_battle(self):
        self.page = "battle"
        self.timed_actor = None
        self.reset_turn_deadline()
        self.advance_automated_turns()

    def reset_turn_deadline(self):
        self.timed_actor = None
        self.turn_deadline_ms = pygame.time.get_ticks() + self.turn_time_limit * 1000

    def check_turn_timeout(self):
        battle = self.battle
        if self.page != "battle" or not battle or battle.winner:
            return
        actor = battle.current
        if not actor or actor.side not in ("player", "rival"):
            return
        identity = (battle.round, battle.turn_index, id(actor))
        if identity != self.timed_actor:
            self.timed_actor = identity
            self.turn_deadline_ms = pygame.time.get_ticks() + self.turn_time_limit * 1000
            return
        if pygame.time.get_ticks() >= self.turn_deadline_ms:
            battle.say(f"O tempo de {actor.name} acabou; ele defendeu automaticamente.")
            battle.defend(actor)
            self.notify("Tempo esgotado: defesa automática.")
            self.advance_automated_turns()

    def draw_battle(self):
        battle = self.battle
        if not battle:
            return
        if battle.winner:
            self.page = "results"
            self.draw_results()
            return
        actor = battle.current
        self.screen.fill((8, 13, 22))
        self.text_fit(f"RODADA {battle.round}  ·  {battle.mode.upper()}", 32, 12, 380, CYAN, self.small)
        remaining = max(0, (self.turn_deadline_ms - pygame.time.get_ticks() + 999) // 1000) if self.turn_deadline_ms else self.turn_time_limit
        timer_color = RED if remaining <= 10 else GOLD
        timer_rect = pygame.Rect(1038, 4, 214, 28)
        pygame.draw.rect(self.screen, PANEL2, timer_rect, border_radius=8)
        pygame.draw.rect(self.screen, timer_color, timer_rect, 2, border_radius=8)
        self.text_fit(f"TEMPO  {remaining // 60:02}:{remaining % 60:02}",
                      timer_rect.x + 8, timer_rect.y + 1, timer_rect.w - 16, timer_color, self.medium, align="center")
        self.text_fit(f"Clima: {CLIMAS[battle.weather]['nome']}  ·  Terreno: {battle.terrain}", 430, 12, 570, MUTED, self.small)
        self.draw_team_status(battle.players, 28, 34, BLUE, "Equipe A", actor)
        self.draw_team_status(battle.enemies, 742, 34, RED, "Equipe B", actor)
        self.draw_battlefield(battle.players, battle.enemies, actor, battle)

        self.panel((28, 510, 710, 222), "Batalha", accent=CYAN)
        self.panel((758, 510, 494, 222), "Ações", accent=GOLD)
        if actor:
            self.text_fit(f"O que {actor.name} fará?", 50, 548, 660, GOLD, self.medium)
            lines = battle.log[-4 - self.history_scroll:len(battle.log) - self.history_scroll if self.history_scroll else None]
            for i, line in enumerate(lines[-4:]):
                self.text_fit("› " + line, 52, 594 + i * 27, 660,
                              TEXT if i == len(lines[-4:]) - 1 else MUTED, self.small)
            role = actor.data.get("funcao", "DPS")
            difficulty = actor.data.get("dificuldade", "Média")
            domain = f" · Domínio: {actor.domain_name}" if actor.domain_turns else ""
            bravery = f" · Bravura {actor.bravery_streak}/10" if actor.kind == "boxeador" else ""
            has_counted_special = any(int(ATAQUES[name].get("requer", 0)) > 0
                                      for name in actor.available_attacks())
            attack_progress = f" · Ataques feitos {actor.attack_count}" if has_counted_special else ""
            shield_state = f"ESC {actor.shield}/{actor.max_shield}"
            if actor.shield_recharge:
                shield_state += f" · recarga {actor.shield_recharge}"
            self.text_fit(f"Turno {actor.turns_taken} · {role} · {difficulty}{bravery}{attack_progress}{domain}", 780, 550, 450, GOLD, self.small)
            self.text_fit(f"HP {actor.hp}/{actor.max_hp} · DEF {actor.data.get('defesa', 0)} · {shield_state} · EN {actor.energy}", 780, 568, 450, MUTED, self.small)
            if self.pending_attack:
                self.draw_target_actions(actor)
            elif self.pending_item:
                self.draw_item_targets(actor)
            elif self.pending_transform:
                self.draw_transform_options(actor)
            elif self.pending_contract:
                self.draw_contract_options(actor)
            else:
                self.draw_action_buttons(actor)

    def draw_team_status(self, team, x, y, accent, title, actor):
        self.panel((x, y, 510, 116), title, accent=accent)
        for i, fighter in enumerate(team[:4]):
            col, row = i % 2, i // 2
            card = pygame.Rect(x + 12 + col * 244, y + 42 + row * 34, 232, 30)
            pygame.draw.rect(self.screen, (31, 42, 60), card, border_radius=7)
            pygame.draw.rect(self.screen, GOLD if fighter is actor else (55, 72, 94), card,
                             2 if fighter is actor else 1, border_radius=7)
            heading = self.fighter_heading(fighter)
            self.text_fit(heading, card.x + 8, card.y + 2, 140, TEXT if fighter.alive else MUTED, self.small)
            hp_text = f"{fighter.hp}/{fighter.max_hp}"
            self.text_fit(hp_text, card.right - 78, card.y + 2, 70, TEXT, self.small)
            self.bar(card.x + 8, card.y + 19, card.w - 16, 6, fighter.hp, fighter.max_hp,
                     GREEN if fighter.hp / max(1, fighter.max_hp) > .5 else GOLD if fighter.hp else RED)

    def draw_battlefield(self, team_a, team_b, actor, battle):
        field = pygame.Rect(28, 162, 1224, 332)
        terrain_art = self.get_visual_art("terrain", battle.terrain)
        if terrain_art:
            background = pygame.transform.smoothscale(terrain_art, field.size)
            background.set_alpha(150)
            self.screen.blit(background, field.topleft)
            shade = pygame.Surface(field.size, pygame.SRCALPHA)
            shade.fill((8, 13, 22, 105))
            self.screen.blit(shade, field.topleft)
        else:
            pygame.draw.rect(self.screen, (14, 22, 32), field, border_radius=14)
            # Faixas discretas mantêm o campo neutro quando não há arte de terreno.
            for y in range(field.y + 12, field.bottom - 8, 18):
                pygame.draw.line(self.screen, (17, 27, 37), (field.x + 4, y), (field.right - 4, y), 1)
        pygame.draw.rect(self.screen, (42, 59, 70), field, 1, border_radius=14)
        self.draw_stage_team(team_a, (40, 190, 565, 486), actor, BLUE, False)
        self.draw_stage_team(team_b, (675, 190, 565, 462), actor, RED, True)

    def draw_stage_team(self, team, area, actor, accent, flip):
        x, y, width, baseline = area
        count = max(1, min(4, len(team)))
        slot_width = width / count
        image_size = 218 if count == 1 else 162 if count == 2 else 128
        image_height = image_size
        for i, fighter in enumerate(team[:4]):
            center_x = round(x + slot_width * (i + .5))
            base_y = baseline - (24 if flip else 0)
            shadow_width = image_size * .72
            pygame.draw.ellipse(self.screen, (27, 49, 54),
                                (round(center_x - shadow_width / 2), base_y - 15, round(shadow_width), 26))
            pygame.draw.ellipse(self.screen, accent, (round(center_x - shadow_width / 2), base_y - 15,
                                                      round(shadow_width), 26), 2)
            art = self.get_character_art("enemy" if fighter.kind in INIMIGOS else "class",
                                         fighter.kind, fighter.form)
            image_rect = pygame.Rect(center_x - image_size // 2, base_y - image_height, image_size, image_height)
            if art:
                self.blit_art(art, image_rect, flip=flip)
            else:
                pygame.draw.circle(self.screen, accent, image_rect.center, image_size // 3)
                self.text_fit(fighter.kind.title(), image_rect.x, image_rect.bottom - 30,
                              image_rect.width, TEXT, self.small)
            if fighter is actor:
                pygame.draw.rect(self.screen, GOLD, image_rect, 2, border_radius=8)
            if not fighter.alive:
                veil = pygame.Surface(image_rect.size, pygame.SRCALPHA)
                veil.fill((8, 10, 16, 150))
                self.screen.blit(veil, image_rect.topleft)

    @staticmethod
    def fighter_heading(fighter):
        character = fighter.kind.replace("_", " ").title()
        if fighter.side == "enemy":
            return f"Robô · {character}"
        return f"{fighter.name} · {character}"

    def bar(self, x, y, w, h, value, maximum, color):
        pygame.draw.rect(self.screen, (12, 17, 27), (x, y, w, h), border_radius=5)
        ratio = max(0, min(1, value / max(1, maximum)))
        pygame.draw.rect(self.screen, color, (x, y, max(3, round(w * ratio)), h), border_radius=5)

    def draw_action_buttons(self, actor):
        labels = [("Atacar", "attack"), ("Defender", "defend"), ("Mochila", "item"),
                  ("Transformar", "transform"), ("Contrato", "contract"), ("Descansar", "rest"),
                  ("Fugir", "flee"), ("Parar batalha", "quit")]
        for i, (label, action) in enumerate(labels):
            row, col = divmod(i, 2)
            enabled = True
            if action == "contract":
                enabled = bool(self.battle.contract_options(actor)) and not actor.contract and not actor.form and "contrato" not in actor.restrictions
            elif action == "transform":
                enabled = (bool(actor.data.get("formas")) and not actor.transform_used and not actor.contract
                           and not actor.form and "transformar" not in actor.restrictions)
                if actor.kind == "boxeador":
                    enabled = enabled and actor.bravery_streak >= 5
            elif action == "defend":
                enabled = (actor.side in ("player", "rival") and actor.max_shield > 0
                           and actor.shield > 0 and actor.shield_recharge == 0)
            self.add_button((778 + col * 228, 598 + row * 33, 216, 30), label,
                            lambda a=action: self.select_action(actor, a),
                            enabled=enabled)

    def draw_contract_options(self, actor):
        if isinstance(self.pending_contract, str):
            targets = self.battle.living(self.battle.enemies if actor.side in ("player", "rival") else self.battle.players)
            self.text_fit("Escolha o adversário que será ligado pelas correntes:", 778, 568, 444, GOLD, self.small)
            for i, target in enumerate(targets[:8]):
                self.add_button((778 + (i % 2) * 228, 592 + (i // 2) * 32, 216, 28), target.name,
                                lambda t=target: self.choose_contract_target(actor, t))
            self.add_button((778, 720, 444, 26), "Voltar aos contratos", lambda: setattr(self, "pending_contract", True))
            return
        contracts = [(name, CONTRATOS[name]) for name in self.battle.contract_options(actor)]
        for i, (name, data) in enumerate(contracts[:4]):
            row, col = divmod(i, 2)
            x = 778 + col * 228
            y = 592 + row * 48
            self.add_button((x, y, 216, 30), name, lambda n=name: self.choose_contract(actor, n))
            description = data.get("descricao", "")
            benefit = description.split(". Não pode", 1)[0].rstrip(".")
            self.text_fit(benefit, x, y + 31, 216, MUTED, self.small)
        self.add_button((778, 704, 444, 28), "Cancelar contrato", lambda: setattr(self, "pending_contract", False))

    def choose_contract(self, actor, name):
        if name == "contrato das correntes igualitárias de fogo":
            self.pending_contract = name
            return
        previous = actor.contract
        self.battle.sign_contract(actor, name)
        self.pending_contract = False
        if actor.contract != previous:
            self.advance_automated_turns()

    def choose_contract_target(self, actor, target):
        contract_name = self.pending_contract
        previous = actor.contract
        self.battle.sign_contract(actor, contract_name, target)
        self.pending_contract = False
        if actor.contract != previous:
            self.advance_automated_turns()

    def select_action(self, actor, action):
        if action == "attack":
            self.pending_attack = "choose"
            self.attack_page = 0
        elif action == "item":
            self.pending_item = "choose"
            self.page = "backpack"
        elif action == "defend":
            self.battle.defend(actor)
            self.advance_automated_turns()
        elif action == "rest":
            self.battle.rest(actor)
            self.advance_automated_turns()
        elif action == "flee":
            self.battle.flee(actor)
            self.advance_automated_turns()
        elif action == "quit":
            self.battle.quit_battle(actor)
            self.page = "results"
        elif action == "transform":
            forms = actor.data.get("formas", [])
            if len(forms) > 1:
                self.pending_transform = True
            elif forms:
                self.choose_transform(actor, forms[0].get("nome"))
        elif action == "contract":
            if self.battle.contract_options(actor) and not actor.contract and not actor.form and "contrato" not in actor.restrictions:
                self.pending_contract = True
            else:
                self.battle.say("Este personagem ainda não tem contrato disponível ou está impedido de assinar.")

    def draw_transform_options(self, actor):
        forms = actor.data.get("formas", [])
        if not forms:
            self.pending_transform = False
            return
        for i, form in enumerate(forms[:4]):
            col, row = i % 2, i // 2
            rect = (778 + col * 228, 594 + row * 52, 216, 48)
            self.choice_card(rect, form.get("nome", "Transformação"),
                             form.get("descricao", "Forma especial"), False,
                             lambda name=form.get("nome"): self.choose_transform(actor, name), GOLD)
        self.add_button((778, 696, 444, 28), "Cancelar transformação", self.cancel_transform)

    def choose_transform(self, actor, form_name):
        self.pending_transform = False
        self.battle.transform(actor, form_name)
        self.advance_automated_turns()

    def cancel_transform(self):
        self.pending_transform = False

    def draw_target_actions(self, actor):
        if self.pending_attack == "choose":
            category_order = {"fisico": 0, "magico": 1, "efeito": 2, "especial": 3}
            all_attacks = sorted(actor.available_attacks(), key=lambda name: (
                category_order.get("especial" if int(ATAQUES[name].get("requer", 0)) else ATAQUES[name].get("categoria", "fisico"), 4), name))
            page_size = 4
            page_count = max(1, (len(all_attacks) + page_size - 1) // page_size)
            self.attack_page = min(self.attack_page, page_count - 1)
            attacks = all_attacks[self.attack_page * page_size:(self.attack_page + 1) * page_size]
            self.text_fit(f"Página {self.attack_page + 1}/{page_count} · {len(all_attacks)} ataques", 778, 590, 440, MUTED, self.small)
            for i, name in enumerate(attacks):
                data = ATAQUES[name]
                required = int(data.get("requer", 0))
                category = "especial" if required else data.get("categoria", "fisico")
                suffix = f" · {actor.attack_count}/{required} ataques" if required else ""
                self.add_button((778 + (i % 2) * 228, 610 + (i // 2) * 40, 216, 34),
                                f"{category.title()} · {name} · {data.get('prioridade', 0)} P{suffix}",
                                lambda n=name: self.choose_attack(n))
            self.add_button((778, 696, 132, 28), "Anterior", lambda: self.scroll_attacks(-1), enabled=self.attack_page > 0)
            self.add_button((918, 696, 132, 28), "Próxima", lambda: self.scroll_attacks(1), enabled=self.attack_page < page_count - 1)
            self.add_button((1058, 696, 164, 28), "Cancelar", lambda: setattr(self, "pending_attack", None))
        else:
            attack_data = ATAQUES.get(self.pending_attack, {})
            util = attack_data.get("util", {})
            own_team = self.battle.players if actor.side == "player" else self.battle.enemies
            enemy_team = self.battle.enemies if actor.side == "player" else self.battle.players
            if util.get("sacrificio"):
                if self.battle.mode not in ("dupla", "bots"):
                    self.text_fit("Sacrifício só está disponível em Dupla ou Grupo vs bots.", 778, 594, 444, RED, self.small)
                    self.add_button((778, 696, 444, 28), "Voltar aos ataques", lambda: setattr(self, "pending_attack", "choose"))
                    return
                targets = self.battle.living(own_team) + self.battle.living(enemy_team)
            elif util and any(key in util for key in ("cura", "energia", "buff", "protecao", "alvos", "ligacao_igualitaria")):
                targets = self.battle.living(own_team)
            else:
                targets = self.battle.living(enemy_team)
            if self.pending_attack and util.get("ligacao_igualitaria"):
                targets = [fighter for fighter in self.battle.living(own_team) if fighter is not actor]
            for i, target in enumerate(targets[:8]):
                self.add_button((778 + (i % 2) * 228, 592 + (i // 2) * 32, 216, 28), target.name,
                                lambda t=target: self.resolve_attack(actor, t))
            self.add_button((778, 720, 444, 26), "Voltar aos ataques", lambda: setattr(self, "pending_attack", "choose"))

    def choose_attack(self, name):
        actor = self.battle.current
        if not actor:
            return
        attack_data = ATAQUES[name]
        required = int(attack_data.get("requer", 0))
        if required and actor.attack_count < required:
            message = f"{name} exige {required} ataques feitos; você fez {actor.attack_count}."
            self.battle.say(message)
            self.notify(message)
            return
        util = attack_data.get("util", {})
        needs_target = any(key in util for key in ("cura", "energia", "buff", "protecao", "alvos", "ligacao_igualitaria", "sacrificio"))
        if attack_data.get("area") or (util and not needs_target):
            targets = self.battle.living(self.battle.enemies if actor.side == "player" else self.battle.players)
            self.resolve_attack(actor, targets[0] if targets else actor, name)
        else:
            self.pending_attack, self.pending_item = name, None

    def scroll_attacks(self, direction):
        self.attack_page = max(0, self.attack_page + direction)

    def resolve_attack(self, actor, target, name=None):
        name = name or self.pending_attack
        if name == "choose":
            return
        attack_data = ATAQUES.get(name, {})
        required = int(attack_data.get("requer", 0))
        if required and actor.attack_count < required:
            message = f"{name} exige {required} ataques feitos; você fez {actor.attack_count}."
            self.battle.say(message)
            self.notify(message)
            self.pending_attack = "choose"
            return
        self.battle.attack(actor, name, target)
        self.pending_attack = None
        self.advance_automated_turns()

    def draw_item_targets(self, actor):
        if self.pending_item == "choose":
            self.page = "backpack"
        else:
            item_kind = ITENS.get(self.pending_item, {}).get("tipo")
            if item_kind == "alma":
                self.text_fit("Escolha o bônus da alma:", 778, 568, 444, GOLD, self.small)
                for i, (label, choice) in enumerate((("Ataque +25%", "forca"), ("Defesa +10", "defesa"), ("Energia cheia", "energia"))):
                    self.add_button((778 + (i % 2) * 228, 594 + (i // 2) * 42, 216, 34), label,
                                    lambda c=choice: self.resolve_item(actor, actor, c))
                self.add_button((778, 690, 444, 30), "Voltar à mochila", self.cancel_item_target)
                return
            ally_item = item_kind in {"cura", "energia", "antidoto", "ressusitador", "forca", "aleatorio", "velocidade", "tipagem", "maximizadora", "vinho", "alma"}
            target_own_team = ally_item
            if item_kind in {"fumaca", "negacao", "barril"}:
                target_own_team = True
            if item_kind in {"bomba", "pedra", "climatica", "vulnerabilidade", "troca_atributos"}:
                target_own_team = False
            own_team = self.battle.players if actor.side == "player" else self.battle.enemies
            enemy_team = self.battle.enemies if actor.side == "player" else self.battle.players
            if item_kind == "troca_atributos":
                eligible = [fighter for fighter in self.battle.living(own_team) + self.battle.living(enemy_team)
                            if fighter is not actor]
            else:
                eligible = self.battle.living(own_team if target_own_team else enemy_team)
            for i, target in enumerate(eligible[:8]):
                self.add_button((778 + (i % 2) * 228, 592 + (i // 2) * 32, 216, 28), target.name,
                                lambda t=target: self.resolve_item(actor, t))
            self.add_button((778, 720, 444, 26), "Voltar à mochila", self.cancel_item_target)

    def choose_item(self, name):
        self.pending_item = name
        if ITENS.get(name, {}).get("tipo") == "barril":
            self.page = "barrel"
        else:
            self.page = "battle"

    def cancel_item_target(self):
        self.pending_item = "choose"
        self.page = "backpack"

    def draw_backpack(self):
        if not self.battle:
            self.page = "home"
            return
        self.screen.fill(BG)
        self.header("Batalha", "Mochila", "Selecione um consumível; depois escolha o alvo.")
        self.panel((28, 154, 1224, 508), "Consumíveis", accent=GOLD)
        actor = self.battle.current
        item_names = [name for name in ITENS
                      if self.inventory.get(name, 0) > 0
                      and (name != "alma" or (actor and actor.relic == "máscara de esqueleto"))]
        per_page = 20
        page_count = max(1, (len(item_names) + per_page - 1) // per_page)
        self.item_page = min(self.item_page, page_count - 1)
        visible_names = item_names[self.item_page * per_page:(self.item_page + 1) * per_page]
        if not item_names:
            self.text_fit("Nenhum consumível escolhido para esta batalha.", 80, 390, 1120, MUTED, self.font, align="center")
        for index, name in enumerate(visible_names):
            data = ITENS[name]
            col, row = index % 4, index // 4
            x, y = 42 + col * 300, 214 + row * 88
            count = self.inventory.get(name, 0)
            detail = data.get("descricao", "Consumível sem descrição.")
            self.choice_card((x, y, 282, 66), f"{name}  ×{count}", detail, False,
                             lambda n=name: self.choose_item(n), GOLD,
                             image=self.get_visual_art("items", name), enabled=count > 0)
        self.add_button((42, 674, 190, 42), "← Voltar à batalha", self.close_backpack)
        if page_count > 1:
            self.add_button((1000, 674, 104, 42), "Anterior", lambda: self.scroll_items(-1), enabled=self.item_page > 0)
            self.text_fit(f"Página {self.item_page + 1}/{page_count}", 1105, 688, 92, MUTED, self.small)
            self.add_button((1198, 674, 54, 42), "→", lambda: self.scroll_items(1), enabled=self.item_page + 1 < page_count)

    def draw_barrel(self):
        actor = self.battle.current if self.battle else None
        if not actor:
            self.page = "home"
            return
        self.screen.fill(BG)
        self.header("Batalha", "Barril", "Guarde até 3 consumíveis ou retire um item armazenado.")
        self.panel((28, 154, 1224, 508), "Itens permitidos", accent=GOLD)
        excluded_types = {"cura", "energia", "forca", "aleatorio", "velocidade", "alma", "pedra"}
        eligible = [name for name, amount in self.inventory.items()
                    if amount > 0 and ITENS.get(name, {}).get("tipo") not in excluded_types
                    and "poção" not in name.casefold() and "pocao" not in name.casefold()]
        contents = actor.data.get("barril_conteudo", [])
        self.text_fit(f"Armazenados: {len(contents)}/3", 50, 188, 500, CYAN, self.small)
        for i, name in enumerate(eligible[:16]):
            col, row = i % 4, i // 4
            x, y = 42 + col * 300, 220 + row * 78
            self.choice_card((x, y, 282, 62), f"Guardar: {name} ×{self.inventory[name]}", ITENS[name].get("descricao", ""), False,
                             lambda n=name: self.resolve_item(actor, actor, n), GOLD,
                             enabled=len(contents) < 3)
        base_y = 536
        for i, name in enumerate(contents[:3]):
            self.add_button((42 + i * 300, base_y, 280, 38), f"Retirar: {name}",
                            lambda n=name: self.resolve_item(actor, actor, "retirar:" + n))
        self.add_button((42, 674, 190, 42), "← Voltar à mochila", self.cancel_item_target)

    def close_backpack(self):
        self.pending_item = None
        self.page = "battle"

    def scroll_items(self, direction):
        if self.page == "backpack" and self.battle:
            actor = self.battle.current
            available = [name for name in ITENS if self.inventory.get(name, 0) > 0
                         and (name != "alma" or (actor and actor.relic == "máscara de esqueleto"))]
        elif self.page == "setup":
            available = [name for name in ITENS if name != "alma" or self.setup_player_has_mask()]
        else:
            available = list(ITENS)
        page_count = max(1, (len(available) + 19) // 20)
        self.item_page = max(0, min(page_count - 1, self.item_page + direction))

    def resolve_item(self, actor, target, choice=None):
        self.battle.use_item(actor, self.pending_item, target, self.inventory, choice)
        self.pending_item = None
        self.advance_automated_turns()

    def advance_automated_turns(self):
        if not self.battle or self.battle.winner:
            return
        while (self.battle.current and self.battle.current.side not in ("player", "rival")):
            actor = self.battle.current
            self.battle.ai_action(actor)
            if self.battle.winner:
                break
        if self.battle.winner:
            self.page = "results"

    def draw_results(self):
        if not self.battle:
            return
        winner = self.battle.winner
        title = {"player": "Vitória!", "enemy": "Derrota", "escape": "Batalha encerrada", "quit": "Batalha interrompida"}.get(winner, "Batalha encerrada")
        self.text("RESULTADO DA BATALHA", 62, 60, CYAN, self.medium)
        self.text(title, 60, 104, TEXT, self.large)
        subtitle = "Seu grupo venceu." if winner == "player" else "Todos os combatentes do grupo foram derrotados." if winner == "enemy" else "Você encerrou a batalha." if winner == "quit" else "Seu grupo fugiu da batalha."
        self.text(subtitle, 64, 164, MUTED)
        self.panel((62, 230, 540, 350), "Estatísticas")
        self.panel((624, 230, 594, 382), "Registro da partida", accent=GOLD)
        self.text(f"Turnos: {self.battle.round}", 90, 292, TEXT)
        self.text(f"Clima final: {CLIMAS[self.battle.weather]['nome']}", 90, 328, TEXT)
        self.text("Dano causado", 90, 382, CYAN, self.medium)
        y = 422
        for name, value in self.battle.damage_dealt.items():
            self.text(f"{name}: {value}", 96, y, TEXT, self.small); y += 24
        self.text("Dano recebido", 324, 382, GOLD, self.medium)
        y = 422
        for name, value in self.battle.damage_received.items():
            self.text(f"{name}: {value}", 330, y, TEXT, self.small); y += 24
        log_lines = self.battle.log
        visible_count = 11
        max_scroll = max(0, len(log_lines) - visible_count)
        self.result_log_scroll = max(0, min(max_scroll, self.result_log_scroll))
        end = len(log_lines) - self.result_log_scroll
        start = max(0, end - visible_count)
        for index, line in enumerate(log_lines[start:end]):
            self.text_fit(f"{start + index + 1}. {line}", 644, 276 + index * 22, 552, MUTED, self.small)
        self.add_button((644, 536, 118, 30), "↑ Mais antigos", lambda: self.scroll_result_log(1),
                        enabled=self.result_log_scroll < max_scroll)
        self.text_fit(f"{start + 1 if end else 0}–{end} de {len(log_lines)}", 773, 544, 290, MUTED, self.small, align="center")
        self.add_button((1070, 536, 128, 30), "Mais recentes ↓", lambda: self.scroll_result_log(-1),
                        enabled=self.result_log_scroll > 0)
        self.add_button((644, 574, 554, 30), "Copiar registro completo", self.copy_battle_log)
        self.add_button((64, 624, 230, 52), "Nova batalha", lambda: self.go_setup(), fill=(37, 94, 102))
        self.add_button((312, 624, 230, 52), "Menu principal", lambda: self.go("home"))

    def scroll_result_log(self, direction):
        self.result_log_scroll = max(0, self.result_log_scroll + direction * 8)

    def copy_battle_log(self):
        if not self.battle:
            return
        try:
            pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, "\n".join(self.battle.log).encode("utf-8"))
        except (AttributeError, pygame.error):
            self.notify("Não foi possível acessar a área de transferência.")
            return
        self.notify("Registro completo copiado.")

    def draw_dev(self):
        self.header("Dev Tools", "Ambiente de teste", "Console de comandos e Dummy de 5000 HP para exercitar as regras do combate.")
        if not self.dev_dummy:
            self.dev_dummy = Fighter.create("Dummy", "enemy", "dummy", {"vida": 5000, "energia": 0, "velocidade": 1, "defesa": 0, "critico": 0})
        if not self.dev_battle:
            tester = Fighter.create("Testador", "player", "cavaleiro", CLASSES["cavaleiro"])
            self.dev_battle = Battle([tester], [self.dev_dummy], "dev")
        self.panel((42, 162, 270, 488), "Dummy", accent=GOLD)
        self.text(f"HP {self.dev_dummy.hp}/{self.dev_dummy.max_hp}", 60, 222, TEXT, self.medium)
        self.bar(60, 264, 234, 16, self.dev_dummy.hp, self.dev_dummy.max_hp, GREEN)
        self.text("EN 0 · DEF 0", 60, 298, MUTED, self.small)
        self.text("VEL 1 · CRIT 0", 60, 320, MUTED, self.small)
        self.text("Efeitos ativos", 60, 362, CYAN, self.font)
        self.text_fit(", ".join(self.dev_dummy.effects) or "Nenhum", 60, 392, 234, TEXT)
        self.text("Terreno", 60, 438, CYAN, self.font)
        self.text_fit(self.dev_battle.terrain if self.dev_battle else "Campo comum", 60, 468, 234, TEXT)
        self.add_button((60, 544, 234, 42), "Reiniciar Dummy", self.reset_dummy)
        self.panel((332, 162, 580, 488), "Comandos", accent=CYAN)
        self.text("Digite um comando e pressione Enter:", 354, 220, MUTED, self.small)
        pygame.draw.rect(self.screen, (15, 22, 35), (352, 247, 540, 48), border_radius=9)
        pygame.draw.rect(self.screen, CYAN, (352, 247, 540, 48), 1, border_radius=9)
        self.text_fit(self.dev_input or "@apply_burn", 368, 261, 508, TEXT if self.dev_input else MUTED)
        self.text("COMANDOS ACEITOS", 354, 310, GOLD, self.small)
        command_help = (
            "Efeitos rápidos: @apply_freezy, @apply_shock, @apply_burn",
            "@apply_slow, @apply_toxic, @apply_blooding, @apply_scary",
            "@apply_effect in (efeito)  |  @apply_effect in all",
            "@apply_elemente_terrain in (nome do terreno)",
            "@apply_combination in @n (elemento + elemento)",
            "@apply_transform in @n (classe, inimigo ou forma)",
            "@apply_hit_kill in dummy",
        )
        for i, line in enumerate(command_help):
            self.text_fit(line, 354, 332 + i * 19, 536, MUTED, self.small)
        self.text("Registro recente", 354, 474, CYAN, self.small)
        log_y = 496
        for line in self.dev_log[-4:]:
            self.text_fit(line, 354, log_y, 536, MUTED, self.small)
            log_y += 19
        if self.dev_waiting_confirmation:
            self.add_button((354, 588, 250, 40), "Funcionou", lambda: self.record_dev_result(True), fill=(38, 91, 69), accent=GREEN)
            self.add_button((626, 588, 250, 40), "Não funcionou", lambda: self.record_dev_result(False), accent=RED)
        self.panel((932, 162, 306, 488), "Resultados", accent=GOLD)
        self.text_fit(f"FUNCIONANDO · {len(self.dev_working)}", 952, 220, 266, GREEN, self.font)
        self.paragraph(", ".join(self.dev_working[-7:]) or "Ainda sem registros", 952, 252, 266, MUTED, self.small)
        self.text_fit(f"NÃO FUNCIONANDO · {len(self.dev_failing)}", 952, 396, 266, RED, self.font)
        self.paragraph(", ".join(self.dev_failing[-7:]) or "Ainda sem registros", 952, 428, 266, MUTED, self.small)
        self.add_button((42, 680, 190, 44), "← Configurações", lambda: self.go("settings"))

    @property
    def dev_log(self):
        if not hasattr(self, "_dev_log"):
            self._dev_log = ["Aguardando comando de teste."]
        return self._dev_log

    def reset_dummy(self):
        self.dev_dummy = Fighter.create("Dummy", "enemy", "dummy", {"vida": 5000, "energia": 0, "velocidade": 1, "defesa": 0, "critico": 0})
        tester = Fighter.create("Testador", "player", "cavaleiro", CLASSES["cavaleiro"])
        self.dev_battle = Battle([tester], [self.dev_dummy], "dev")
        self.notify("Dummy reiniciado.")

    def run_dev_command(self):
        command = self.dev_input.strip()
        if not command:
            return
        normalized = command.lower()
        aliases = {"@apply_freezy": "congelado", "@apply_shock": "paralisado", "@apply_burn": "queima",
                   "@apply_slow": "lento", "@apply_toxic": "veneno", "@apply_blooding": "sangramento",
                   "@apply_scary": "medo"}
        if normalized.startswith("@apply_effect in "):
            effect = normalized.split(" in ", 1)[1].strip(" ()")
            effect = {"freezy": "congelado", "shock": "paralisado", "burn": "queima", "slow": "lento",
                      "toxic": "veneno", "blooding": "sangramento", "scary": "medo"}.get(effect, effect)
            if effect in ("efeitos", "todos", "all"):
                for status in EFEITOS:
                    self.dev_battle.apply_effect(self.dev_dummy, status, 3)
            else:
                self.dev_battle.apply_effect(self.dev_dummy, effect, 3)
        elif normalized in aliases:
            self.dev_battle.apply_effect(self.dev_dummy, aliases[normalized], 3)
        elif normalized.startswith("@apply_elemente_terrain in "):
            terrain = command.split(" in ", 1)[1].strip(" ()")
            self.dev_battle.set_terrain(terrain)
        elif normalized.startswith(("@applt_combination in @n ", "@apply_combination in @n ")):
            combination = command.split("@n ", 1)[1].strip(" ()")
            self.dev_battle.apply_combination(combination)
        elif normalized == "@apply_hit_kill in dummy":
            self.dev_dummy.hp = 0
            self.dev_dummy.alive = False
            self.dev_log.append("Dummy eliminado instantaneamente.")
        elif normalized.startswith("@apply_transform in @n "):
            values = [part.strip(" ()") for part in command.split("@n ", 1)[-1].split(",") if part.strip(" (),")]
            target_name = next((v.casefold() for v in values if v.casefold() in INIMIGOS or v.casefold() in CLASSES), None)
            if target_name in INIMIGOS:
                self.dev_dummy.kind, self.dev_dummy.data = target_name, dict(INIMIGOS[target_name])
                self.dev_dummy.form = None
                self.dev_log.append(f"Dummy transformado em {target_name}.")
            elif target_name in CLASSES:
                self.dev_dummy.kind, self.dev_dummy.data = target_name, dict(CLASSES[target_name])
                self.dev_dummy.form = None
                self.dev_log.append(f"Dummy transformado na classe {target_name}.")
            else:
                self.dev_dummy.form = values[-1] if values else "Forma de teste"
                self.dev_log.append(f"Transformação de teste: {self.dev_dummy.form}.")
        else:
            self.dev_log.append(f"Comando desconhecido: {command}")
            self.dev_waiting_confirmation = command
            self.dev_input = ""
            return
        self.dev_log.extend(self.dev_battle.log[-1:])
        self.dev_waiting_confirmation = command
        self.dev_input = ""

    def record_dev_result(self, worked):
        target = self.dev_working if worked else self.dev_failing
        target.append(self.dev_waiting_confirmation)
        self.save_dev_results()
        self.dev_log.append("Resultado guardado: " + ("funcionando" if worked else "não funcionando"))
        self.dev_waiting_confirmation = None

    def go(self, page):
        self.page = page

    def click(self, pos):
        for button in reversed(self.buttons):
            if button.hit(pos):
                button.action()
                return

    def handle_key(self, event):
        if self.page == "settings" and self.dev_auth_stage:
            if event.key == pygame.K_ESCAPE:
                self.dev_auth_stage = None
                self.dev_auth_input = ""
            elif event.key == pygame.K_RETURN:
                self.submit_dev_auth()
            elif event.key == pygame.K_BACKSPACE:
                self.dev_auth_input = self.dev_auth_input[:-1]
            elif event.unicode.isprintable() and len(self.dev_auth_input) < 64:
                self.dev_auth_input += event.unicode
            return
        if event.key == pygame.K_ESCAPE:
            if self.page == "barrel":
                self.cancel_item_target()
            elif self.page == "backpack":
                if self.pending_item and self.pending_item != "choose":
                    self.pending_item = "choose"
                    self.page = "battle"
                else:
                    self.close_backpack()
            elif self.page == "battle" and self.pending_transform:
                self.cancel_transform()
            elif self.page == "battle" and self.pending_item:
                self.pending_item = "choose"
                self.page = "backpack"
            elif self.page == "battle":
                self.notify("Use a ação Fugir para encerrar a batalha.")
            elif self.page in ("settings", "setup", "dev", "results"):
                self.go("home")
            return
        if self.page == "setup" and self.setup_focus == "player_name":
            i = self.setup_name_index
            value = self.setup_inputs[i]
            if event.key == pygame.K_BACKSPACE:
                self.setup_inputs[i] = value[:-1]
            elif event.key == pygame.K_RETURN:
                self.setup_focus = ""
            elif event.unicode.isprintable() and len(value) < 22:
                self.setup_inputs[i] += event.unicode
        elif self.page == "dev":
            if event.key == pygame.K_RETURN:
                self.run_dev_command()
            elif event.key == pygame.K_BACKSPACE:
                self.dev_input = self.dev_input[:-1]
            elif event.unicode.isprintable() and len(self.dev_input) < 100:
                self.dev_input += event.unicode

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.click(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 4 and self.page == "battle":
                    self.history_scroll = min(len(self.battle.log), self.history_scroll + 2)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5 and self.page == "battle":
                    self.history_scroll = max(0, self.history_scroll - 2)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 4 and self.page == "results":
                    self.scroll_result_log(1)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5 and self.page == "results":
                    self.scroll_result_log(-1)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
            self.check_turn_timeout()
            self.draw()
            self.clock.tick(60)
        pygame.quit()


def run():
    RPGApp().run()
