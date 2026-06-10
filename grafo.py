import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def carregar_grade(caminho_json):
    """Lê o arquivo grade.json e retorna a lista de disciplinas."""
    with open(caminho_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    return dados['disciplinas']

def construir_grafo(disciplinas):
    """
    Constrói um grafo dirigido (DAG) a partir da lista de disciplinas.
    Cada nó representa uma disciplina com seus atributos.
    Cada aresta A -> B significa que A é pré-requisito de B.
    """
    G = nx.DiGraph()

    # Adiciona os nós com seus atributos
    for disc in disciplinas:
        G.add_node(
            disc['codigo'],
            nome=disc['nome'],
            periodo=disc['periodo'],
            semestre_oferta=disc['semestre_oferta'],
            carga_horaria=disc['carga_horaria']
        )

    # Adiciona as arestas (pré-requisitos)
    for disc in disciplinas:
        for prereq in disc['prerequisitos']:
            G.add_edge(prereq, disc['codigo'])

    return G

def visualizar_grafo(G, caminho_saida='grafo.png'):
    """
    Gera uma visualização do grafo organizada por período (1º ao 8º).
    Cores diferentes para semestre de oferta ímpar (azul) e par (laranja).
    """
    fig, ax = plt.subplots(figsize=(24, 14))

    # Posiciona os nós por período (eixo X) e distribui verticalmente (eixo Y)
    pos = {}
    periodos = {}
    for node in G.nodes():
        p = G.nodes[node]['periodo']
        if p not in periodos:
            periodos[p] = []
        periodos[p].append(node)

    for periodo, nos in periodos.items():
        for i, node in enumerate(nos):
            x = (periodo - 1) * 2.5
            y = i * 2 - (len(nos) - 1)
            pos[node] = (x, y)

    # Define cores por semestre de oferta
    cores = []
    for node in G.nodes():
        if G.nodes[node]['semestre_oferta'] == 1:
            cores.append('#4A90D9')   # azul = semestre ímpar
        else:
            cores.append('#E8A838')   # laranja = semestre par

    # Labels curtos para não poluir o grafo
    labels = {node: G.nodes[node]['nome'].replace(' ', '\n') for node in G.nodes()}

    nx.draw_networkx_nodes(G, pos, node_color=cores, node_size=1800, ax=ax)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=5, ax=ax)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=15,
                           edge_color='#555555', width=1.2,
                           connectionstyle='arc3,rad=0.1', ax=ax)

    # Legenda
    legenda = [
        mpatches.Patch(color='#4A90D9', label='Semestre ímpar (1º, 3º, 5º, 7º)'),
        mpatches.Patch(color='#E8A838', label='Semestre par (2º, 4º, 6º, 8º)')
    ]
    ax.legend(handles=legenda, loc='upper right', fontsize=10)

    # Rótulos dos períodos no eixo X
    ax.set_xticks([(p - 1) * 2.5 for p in range(1, 9)])
    ax.set_xticklabels([f'{p}º Período' for p in range(1, 9)], fontsize=10)
    ax.tick_params(left=False, labelleft=False)

    ax.set_title('Grade Curricular — Ciência da Computação UERN 2023.1\nGrafo de Pré-requisitos', fontsize=14)
    plt.tight_layout()
    plt.savefig(caminho_saida, dpi=150, bbox_inches='tight')
    print(f"Grafo salvo em: {caminho_saida}")
    plt.close()

def imprimir_info_grafo(G):
    """Imprime informações básicas sobre o grafo construído."""
    print("=" * 50)
    print("INFORMAÇÕES DO GRAFO")
    print("=" * 50)
    print(f"Total de disciplinas (nós):      {G.number_of_nodes()}")
    print(f"Total de pré-requisitos (arestas): {G.number_of_edges()}")
    print(f"É um DAG (sem ciclos):           {nx.is_directed_acyclic_graph(G)}")
    print()
    print("Disciplinas sem pré-requisitos (raízes do grafo):")
    raizes = [n for n in G.nodes() if G.in_degree(n) == 0]
    for r in raizes:
        print(f"  - {G.nodes[r]['nome']}")
    print()
    print("Disciplinas sem dependentes (folhas do grafo):")
    folhas = [n for n in G.nodes() if G.out_degree(n) == 0]
    for f in folhas:
        print(f"  - {G.nodes[f]['nome']}")

if __name__ == "__main__":
    disciplinas = carregar_grade('grade.json')
    G = construir_grafo(disciplinas)
    imprimir_info_grafo(G)
    visualizar_grafo(G, caminho_saida='grafo.png')
