# RPG de Batalha — versão Pygame

Esta é uma implementação gráfica separada de `batalha.py`. A aplicação reutiliza as tabelas de classes, inimigos, ataques, itens, climas, efeitos, contratos e relíquias desse arquivo, enquanto a lógica de combate e a interface Pygame ficam em módulos próprios.

## Iniciar

1. Instale Python 3.10 ou mais recente.
2. Abra um terminal nesta pasta e execute `python -m pip install -r requirements.txt`.
3. Execute `python pygame_main.py` ou abra `run_pygame.bat`.

## O que já está implementado

- Menu principal, configurações e tela de preparação com clima e ordem inicial dos turnos.
- Batalhas Solo e Dupla contra inimigos controlados por IA.
- Multiplayer local com equipes de 1 a 4 personagens por lado; cada lado escolhe classes ou inimigos.
- Artes de classes, inimigos e megaformas na preparação e no campo de batalha.
- Menu de batalha inspirado em RPGs portáteis, mochila com todos os consumíveis e seleção entre várias megaformas.
- Ações de ataque, defesa, consumíveis, transformação, contrato, descanso e fuga.
- Histórico da batalha, vida, energia, escudo, efeitos e tela de resultado com estatísticas.
- Ambiente de teste com acesso protegido, Dummy, comandos para efeitos, terrenos, combinações, transformação e eliminação, mais registro de testes.
Os resultados do Ambiente de Teste são guardados em `dev_test_results.json` na pasta do projeto.

## Estrutura

- `batalha.py`: dados de conteúdo já existentes.
- `pygame_rpg/engine.py`: combatentes, turnos, cálculo de dano, IA e condições de batalha.
- `pygame_rpg/app.py`: menus, interface e interação Pygame.
- `pygame_main.py`: ponto de entrada.

Este é o primeiro corte jogável da versão Pygame. Mecânicas descritas em `batalha.py` que não estão no motor gráfico ainda podem precisar de adaptação antes de se comportarem exatamente como no jogo de terminal.
