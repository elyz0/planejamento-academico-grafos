#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
planejamento.py — Parte 3
Responsável por:
  1. Implementar a ordenação topológica (Kahn) personalizada no grafo.
  2. Implementar o planejamento do Caso 1 (com semestre de oferta).
  3. Implementar o planejamento do Caso 2 (ignorando semestre de oferta).
  4. Exibir a saída formatada de cada planejamento e uma tabela comparativa.

Uso:
    python3 planejamento.py --grade grade.json --historico /home/luiz/Downloads/historico_20240006973.pdf --max 6
"""

import sys
import argparse
import networkx as nx

# Importa o código das partes anteriores
try:
    from grafo import carregar_grade, construir_grafo
    from entrada import carregar_dados_entrada
except ImportError:
    print("[ERRO] Não foi possível importar 'grafo.py' ou 'entrada.py'. Certifique-se de que estão no mesmo diretório.")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# 1. ORDENAÇÃO TOPOLÓGICA PERSONALIZADA (ALGORITMO DE KAHN)
# ─────────────────────────────────────────────────────────────

def ordenacao_topologica(G):
    """
    Retorna uma ordenação topológica dos nós do grafo G.
    Implementa o algoritmo de Kahn (baseado em graus de entrada).
    Caso o grafo contenha ciclos, lança uma exceção ValueError.
    """
    # Calcula os graus de entrada iniciais
    grau_entrada = {u: 0 for u in G.nodes()}
    for u, v in G.edges():
        grau_entrada[v] += 1
        
    # Inicializa a fila com nós de grau de entrada 0
    # Ordenamos a fila para garantir comportamento determinístico
    fila = [u for u in G.nodes() if grau_entrada[u] == 0]
    fila.sort()
    
    ordenados = []
    while fila:
        u = fila.pop(0)
        ordenados.append(u)
        
        for v in G.successors(u):
            grau_entrada[v] -= 1
            if grau_entrada[v] == 0:
                fila.append(v)
                fila.sort()
                
    if len(ordenados) != G.number_of_nodes():
        raise ValueError("O grafo possui ciclos (não é um DAG). Não é possível realizar a ordenação topológica.")
        
    return ordenados


# ─────────────────────────────────────────────────────────────
# 2. CÁLCULO DE ALTURA DE CADA NÓ (CAMINHO CRÍTICO)
# ─────────────────────────────────────────────────────────────

def calcular_alturas(G):
    """
    Calcula a altura de cada nó no DAG G.
    A altura de um nó u é a quantidade máxima de nós do caminho de u até uma folha.
    Usa a ordenação topológica para calcular de forma dinâmica de trás para frente.
    """
    ordem = ordenacao_topologica(G)
    alturas = {}
    
    # Processa os nós de trás para frente
    for node in reversed(ordem):
        successores = list(G.successors(node))
        if not successores:
            alturas[node] = 1
        else:
            alturas[node] = 1 + max(alturas[s] for s in successores)
            
    return alturas


# ─────────────────────────────────────────────────────────────
# 3. ALGORITMO DE PLANEJAMENTO - CASO 1
# ─────────────────────────────────────────────────────────────

def planejar_caso1(G_orig, max_disciplinas, semestre_inicial):
    """
    Caso 1: Aloca as disciplinas respeitando:
      - Pré-requisitos (arestas do grafo)
      - Limite de disciplinas por semestre (max_disciplinas)
      - Semestre de oferta original (ímpar/par)
      
    Retorna uma lista de dicionários representando cada semestre planejado.
    """
    G = G_orig.copy()
    planejamento = []
    semestre_atual = semestre_inicial
    
    # Limite de segurança para evitar loops infinitos
    limite_segurança = G.number_of_nodes() * 2 + 20
    iteracao = 0
    
    while G.number_of_nodes() > 0 and iteracao < limite_segurança:
        iteracao += 1
        
        # Paridade do semestre planejado (1 = ímpar, 2 = par)
        paridade = 1 if semestre_atual % 2 != 0 else 2
        
        # Nós prontos são aqueles sem pré-requisitos pendentes (grau de entrada 0 no subgrafo G)
        prontas = [n for n in G.nodes() if G.in_degree(n) == 0]
        
        # Filtra as prontas que correspondem à paridade do semestre
        prontas_da_oferta = [n for n in prontas if G.nodes[n]['semestre_oferta'] == paridade]
        
        # Calcula as alturas do subgrafo restante para priorizar o caminho crítico
        alturas_restantes = calcular_alturas(G)
        
        # Ordenação por prioridade:
        # 1. Maior altura (caminho crítico)
        # 2. Menor período recomendado original
        # 3. Maior grau de saída no grafo atual (libera mais dependentes)
        # 4. Código do componente (ordem alfabética para desempate)
        prontas_da_oferta.sort(key=lambda n: (
            -alturas_restantes[n],
            G.nodes[n]['periodo'],
            -G.out_degree(n),
            n
        ))
        
        # Seleciona até o limite máximo de disciplinas
        selecionadas = prontas_da_oferta[:max_disciplinas]
        
        # Registra o semestre (mesmo que fique vazio devido a restrições de oferta)
        planejamento.append({
            'semestre_num': semestre_atual,
            'paridade': paridade,
            'disciplinas': selecionadas
        })
        
        # Remove as disciplinas alocadas do grafo temporário
        G.remove_nodes_from(selecionadas)
        semestre_atual += 1
        
    if G.number_of_nodes() > 0:
        raise ValueError("Erro no planejamento do Caso 1: Não foi possível alocar todas as disciplinas.")
        
    return planejamento


# ─────────────────────────────────────────────────────────────
# 4. ALGORITMO DE PLANEJAMENTO - CASO 2
# ─────────────────────────────────────────────────────────────

def planejar_caso2(G_orig, max_disciplinas, semestre_inicial):
    """
    Caso 2: Aloca as disciplinas respeitando:
      - Pré-requisitos (arestas do grafo)
      - Limite de disciplinas por semestre (max_disciplinas)
      - Ignorando o semestre de oferta (todas as disciplinas disponíveis em qualquer período)
      
    Retorna uma lista de dicionários representando cada semestre planejado.
    """
    G = G_orig.copy()
    planejamento = []
    semestre_atual = semestre_inicial
    
    limite_segurança = G.number_of_nodes() * 2 + 20
    iteracao = 0
    
    while G.number_of_nodes() > 0 and iteracao < limite_segurança:
        iteracao += 1
        paridade = 1 if semestre_atual % 2 != 0 else 2
        
        # Nós prontos
        prontas = [n for n in G.nodes() if G.in_degree(n) == 0]
        
        # No Caso 2, não filtramos por paridade. Todas as disciplinas prontas são candidatas.
        alturas_restantes = calcular_alturas(G)
        
        prontas.sort(key=lambda n: (
            -alturas_restantes[n],
            G.nodes[n]['periodo'],
            -G.out_degree(n),
            n
        ))
        
        selecionadas = prontas[:max_disciplinas]
        
        planejamento.append({
            'semestre_num': semestre_atual,
            'paridade': paridade,
            'disciplinas': selecionadas
        })
        
        G.remove_nodes_from(selecionadas)
        semestre_atual += 1
        
    if G.number_of_nodes() > 0:
        raise ValueError("Erro no planejamento do Caso 2: Não foi possível alocar todas as disciplinas.")
        
    return planejamento


# ─────────────────────────────────────────────────────────────
# 5. FORMATAÇÃO E EXIBIÇÃO DA SAÍDA
# ─────────────────────────────────────────────────────────────

def exibir_planejamento(planejamento, G_ref, titulo):
    """
    Gera e exibe a visualização formatada do planejamento.
    Retorna (total_semestres, carga_horaria_total, disciplinas_totais)
    """
    print("=" * 80)
    print(f" {titulo.upper().center(78)} ")
    print("=" * 80)
    
    carga_total = 0
    total_disciplinas = 0
    semestres_ativos = 0
    
    for sem in planejamento:
        sem_num = sem['semestre_num']
        paridade_str = "Ímpar" if sem['paridade'] == 1 else "Par"
        disciplinas = sem['disciplinas']
        
        print(f"\n⚡ {sem_num}º Semestre Letivo Planejado ({paridade_str})")
        print("─" * 80)
        
        if not disciplinas:
            print("  [Nenhuma disciplina pôde ser alocada neste semestre por restrição de oferta]")
            print("  Carga Horária: 0h | 0 disciplina(s)")
            continue
            
        semestres_ativos += 1
        carga_semestre = 0
        for cod in disciplinas:
            d = G_ref.nodes[cod]
            nome = d['nome']
            ch = d['carga_horaria']
            carga_semestre += ch
            print(f"   [{cod}]  {nome:<45} | {ch:>4}h")
            
        carga_total += carga_semestre
        total_disciplinas += len(disciplinas)
        
        print("─" * 80)
        print(f"  Carga Horária Semestral: {carga_semestre:>4}h | Total de Disciplinas: {len(disciplinas)}")
        
    print("\n" + "=" * 80)
    print(" RESUMO DA SAÍDA:")
    print(f"  • Total de semestres corridos : {len(planejamento)}")
    print(f"  • Semestres com disciplinas   : {semestres_ativos}")
    print(f"  • Carga Horária Total Planejada: {carga_total}h")
    print(f"  • Total de disciplinas alocadas: {total_disciplinas}")
    print("=" * 80 + "\n")
    
    return len(planejamento), carga_total, total_disciplinas


def exibir_comparacao(res_c1, res_c2):
    """Exibe uma tabela comparativa dos resultados obtidos nos casos 1 e 2."""
    sem_c1, ch_c1, disc_c1 = res_c1
    sem_c2, ch_c2, disc_c2 = res_c2
    
    diff_sem = sem_c1 - sem_c2
    
    print("=" * 80)
    print(f" {'TABELA COMPARATIVA'.center(78)} ")
    print("=" * 80)
    print(f" {'Métrica':<35} | {'Caso 1 (Com Oferta)':<20} | {'Caso 2 (Sem Oferta)':<20}")
    print("─" * 80)
    print(f" {'Total de Semestres Necessários':<35} | {sem_c1:<20} | {sem_c2:<20}")
    print(f" {'Carga Horária Planejada':<35} | {f'{ch_c1}h':<20} | {f'{ch_c2}h':<20}")
    print(f" {'Disciplinas Alocadas':<35} | {disc_c1:<20} | {disc_c2:<20}")
    print(f" {'Média de Carga Horária / Semestre':<35} | {f'{ch_c1/sem_c1:.1f}h':<20} | {f'{ch_c2/sem_c2:.1f}h':<20}")
    print("=" * 80)
    
    print("💡 ANÁLISE DE IMPACTO:")
    if diff_sem > 0:
        print(f"  -> A restrição de semestre de oferta (ímpar/par) aumenta o tempo de curso em {diff_sem} semestre(s).")
        print(f"  -> Isso ocorre devido a semestres vazios ou ociosos causados pela indisponibilidade de componentes.")
    elif diff_sem == 0:
        print("  -> Surpreendentemente, desconsiderar o período de oferta das disciplinas não reduziu o número de semestres.")
        print("     Isso indica que o fluxo de pré-requisitos (caminho crítico) é o fator gargalo neste cenário.")
    else:
        print("  -> O Caso 2 levou mais semestres. Isso sugere alguma inconsistência na ordenação.")
    print("=" * 80 + "\n")


# ─────────────────────────────────────────────────────────────
# 6. VISUALIZAÇÃO GRÁFICA DO PLANEJAMENTO (PNG)
# ─────────────────────────────────────────────────────────────

def visualizar_planejamento(plan1, plan2, G_ref, caminho_saida='planejamento.png'):
    """
    Gera uma imagem PNG comparando o planejamento do Caso 1 e do Caso 2.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    max_semestres = max(len(plan1), len(plan2))
    
    # Criamos a figura com fundo escuro elegante
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), facecolor='#0F172A')
    
    # Configurações de fontes
    font_title = {'fontsize': 14, 'color': '#38BDF8', 'weight': 'bold'}
    font_card_code = {'fontsize': 8, 'color': '#38BDF8', 'weight': 'bold'}
    font_card_name = {'fontsize': 8, 'color': '#F1F5F9'}
    font_card_hours = {'fontsize': 8, 'color': '#10B981', 'weight': 'bold'}
    font_sem_footer = {'fontsize': 9, 'color': '#E2E8F0', 'weight': 'bold'}

    # Dicionário de cores para indicar o período original de recomendação
    periodo_colors = {
        1: '#EF4444', 2: '#F97316', 3: '#F59E0B', 4: '#10B981',
        5: '#06B6D4', 6: '#3B82F6', 7: '#6366F1', 8: '#8B5CF6'
    }

    def desenhar_painel(ax, plan, titulo):
        ax.set_facecolor('#0F172A')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.set_title(titulo, fontdict=font_title, pad=15)
        
        if not plan:
            ax.text(0.5, 0.5, "Planejamento vazio", color='#94A3B8', ha='center', va='center', fontsize=12)
            return

        num_colunas = len(plan)
        # Calcula largura da coluna com espaçamento
        col_width = 1.0 / (max_semestres + 0.3)
        
        for i, sem in enumerate(plan):
            sem_num = sem['semestre_num']
            paridade = sem['paridade']
            paridade_str = "Ímpar" if paridade == 1 else "Par"
            disciplinas = sem['disciplinas']
            
            # Posição X da coluna
            x_left = i * (col_width * 1.02) + 0.015
            
            # Desenha o contêiner do semestre
            rect_bg = mpatches.FancyBboxPatch(
                (x_left, 0.05), col_width * 0.96, 0.90,
                boxstyle="round,pad=0.01",
                facecolor='#1E293B', edgecolor='#334155', linewidth=1.5
            )
            ax.add_patch(rect_bg)
            
            # Cabeçalho do Semestre (azul para ímpar, laranja para par)
            header_color = '#60A5FA' if paridade == 1 else '#F59E0B'
            ax.text(
                x_left + col_width / 2.0, 0.91,
                f"{sem_num}º Semestre ({paridade_str})",
                fontdict={'fontsize': 10, 'color': header_color, 'weight': 'bold'},
                ha='center', va='center'
            )
            
            # Limites verticais para os cards
            y_top_limit = 0.86
            y_bottom_limit = 0.14
            available_height = y_top_limit - y_bottom_limit
            
            n_disc = len(disciplinas)
            ch_total = 0
            
            if n_disc > 0:
                gap = 0.012 if n_disc > 1 else 0
                card_height = (available_height - (n_disc - 1) * gap) / n_disc
                
                for idx, cod in enumerate(disciplinas):
                    d = G_ref.nodes[cod]
                    nome = d['nome']
                    ch = d['carga_horaria']
                    ch_total += ch
                    
                    y_pos = y_top_limit - idx * (card_height + gap) - card_height
                    
                    # Card da disciplina
                    rect_card = mpatches.FancyBboxPatch(
                        (x_left + 0.005, y_pos), col_width * 0.90, card_height,
                        boxstyle="round,pad=0.005",
                        facecolor='#334155', edgecolor='#475569', linewidth=1.0
                    )
                    ax.add_patch(rect_card)
                    
                    # Indicador colorido da esquerda
                    p_orig = d.get('periodo', 1)
                    color_indicator = periodo_colors.get(p_orig, '#94A3B8')
                    rect_indicator = mpatches.FancyBboxPatch(
                        (x_left + 0.006, y_pos + 0.002), col_width * 0.025, card_height - 0.004,
                        boxstyle="round,pad=0.001",
                        facecolor=color_indicator, edgecolor='none'
                    )
                    ax.add_patch(rect_indicator)
                    
                    # Código e CH (linha superior do card)
                    ax.text(
                        x_left + col_width * 0.06, y_pos + card_height * 0.72,
                        cod, fontdict=font_card_code, ha='left', va='center'
                    )
                    ax.text(
                        x_left + col_width * 0.84, y_pos + card_height * 0.72,
                        f"{ch}h", fontdict=font_card_hours, ha='right', va='center'
                    )
                    
                    # Nome (truncado se muito longo)
                    nome_exibido = nome if len(nome) <= 26 else nome[:23] + "..."
                    ax.text(
                        x_left + col_width * 0.06, y_pos + card_height * 0.28,
                        nome_exibido, fontdict=font_card_name, ha='left', va='center'
                    )
            else:
                ax.text(
                    x_left + col_width / 2.0, 0.5,
                    "Semestre Ocioso / Vazio\n(Restrição de Oferta)",
                    fontdict={'fontsize': 8.5, 'color': '#64748B', 'style': 'italic'},
                    ha='center', va='center'
                )
            
            # Carga Horária e Disciplinas no rodapé da coluna
            ax.text(
                x_left + col_width / 2.0, 0.08,
                f"{ch_total}h | {n_disc} disc.",
                fontdict=font_sem_footer,
                ha='center', va='center'
            )

    desenhar_painel(ax1, plan1, "Caso 1: Planejamento Curricular (Com Oferta Par/Ímpar)")
    desenhar_painel(ax2, plan2, "Caso 2: Planejamento Curricular (Ignorando Oferta)")
    
    fig.suptitle("PLANEJAMENTO ACADÊMICO - COMPARAÇÃO DE CENÁRIOS", fontsize=18, color='#F8FAFC', weight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(caminho_saida, dpi=180, bbox_inches='tight')
    plt.close()
    print(f"Visualização do planejamento salva em: {caminho_saida}")


# ─────────────────────────────────────────────────────────────
# 7. EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Geração de planejamento acadêmico otimizado via Ordenação Topológica."
    )
    parser.add_argument("--grade", default="grade.json",
                        help="Caminho para grade.json (padrão: grade.json)")
    parser.add_argument("--historico", default=None,
                        help="Caminho para o PDF do histórico escolar SIGAA (opcional)")
    parser.add_argument("--max", type=int, default=6, choices=[5, 6, 7],
                        help="Máx. disciplinas por semestre (padrão: 6)")
    parser.add_argument("--inicio", type=int, default=None,
                        help="Semestre inicial para o planejamento (padrão: derivado do histórico ou 1)")
    args = parser.parse_args()

    # Variáveis do grafo
    G_pendente = None
    semestre_inicial = 1
    
    # Carrega a grade completa como referência para atributos de nós
    try:
        disciplinas_grade = carregar_grade(args.grade)
    except FileNotFoundError:
        print(f"[ERRO] Arquivo de grade não encontrado: {args.grade}")
        sys.exit(1)
        
    # Se o histórico for informado, lê os dados e atualiza o grafo
    if args.historico is not None:
        try:
            # Reutiliza o carregador da entrada.py
            _, G_pendente, sem_atual = carregar_dados_entrada(
                caminho_grade=args.grade,
                caminho_historico=args.historico,
                max_disciplinas=args.max
            )
            
            # Se o semestre inicial não foi informado, decidimos de forma inteligente
            if args.inicio is not None:
                semestre_inicial = args.inicio
            else:
                semestre_inicial = sem_atual if sem_atual is not None else 1
                
        except Exception as e:
            print(f"[ERRO] Falha ao ler histórico: {e}")
            sys.exit(1)
    else:
        # Se não houver histórico, planeja o curso inteiro do início
        print("=" * 60)
        print("CONSTRUINDO GRAFO COMPLETO (Curso Inteiro)")
        print("=" * 60)
        G_completo = construir_grafo(disciplinas_grade)
        G_pendente = G_completo
        
        if args.inicio is not None:
            semestre_inicial = args.inicio
        else:
            semestre_inicial = 1
            
        print(f"      {G_pendente.number_of_nodes()} nós | {G_pendente.number_of_edges()} arestas | "
              f"DAG válido: {nx.is_directed_acyclic_graph(G_pendente)}")
        print(f"      Planejando do início (Semestre {semestre_inicial}).")
        print("=" * 60)

    # 1. Executa Ordenação Topológica Customizada para validar que o grafo é um DAG
    try:
        ordenacao_topologica(G_pendente)
    except ValueError as e:
        print(f"[ERRO] O grafo possui ciclos! Detalhes: {e}")
        sys.exit(1)

    # 2. Executa o Planejamento para o Caso 1
    print("\n[EXECUTANDO CASO 1: COM RESTRIÇÃO DE OFERTA SEMESTRAL]\n")
    plan1 = planejar_caso1(G_pendente, args.max, semestre_inicial)
    # Criamos um grafo completo de referência para buscar atributos que podem ter sumido
    G_ref = construir_grafo(disciplinas_grade)
    res_c1 = exibir_planejamento(plan1, G_ref, "Caso 1: Planejamento Curricular (Com Oferta Par/Ímpar)")
    
    # 3. Executa o Planejamento para o Caso 2
    print("\n[EXECUTANDO CASO 2: IGNORANDO RESTRIÇÃO DE OFERTA SEMESTRAL]\n")
    plan2 = planejar_caso2(G_pendente, args.max, semestre_inicial)
    res_c2 = exibir_planejamento(plan2, G_ref, "Caso 2: Planejamento Curricular (Ignorando Oferta)")

    # 4. Exibe Tabela Comparativa e Análise
    exibir_comparacao(res_c1, res_c2)

    # 5. Gera a visualização gráfica em PNG
    visualizar_planejamento(plan1, plan2, G_ref, 'planejamento.png')


if __name__ == "__main__":
    main()
