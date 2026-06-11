"""
entrada.py — Parte 2 (Bruno Eduardo)
Responsável por:
  1. Ler o histórico escolar do aluno (PDF do SIGAA)
  2. Identificar disciplinas aprovadas
  3. Remover do grafo (construído pela Pessoa 1) as disciplinas aprovadas
  4. Devolver o grafo atualizado com apenas as disciplinas pendentes

Depende de: grafo.py Parte 1 (Elyza) — ambos devem estar na mesma pasta.

Uso standalone:
    python entrada.py --grade grade.json --historico historico.pdf --max 6

Uso como módulo (main.py):
    from grafo import carregar_grade, construir_grafo
    from entrada import ler_historico, remover_aprovadas_do_grafo

    disciplinas = carregar_grade('grade.json')
    G = construir_grafo(disciplinas)

    aprovadas, semestre_atual, todas = ler_historico('historico.pdf')
    G_pendente, _, _ = remover_aprovadas_do_grafo(G, aprovadas, disciplinas, todas)
"""

import re
import sys
import unicodedata
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("[ERRO] Biblioteca 'pdfplumber' não encontrada.")
    print("       Instale com: pip install pdfplumber")
    sys.exit(1)

try:
    import networkx as nx
except ImportError:
    print("[ERRO] Biblioteca 'networkx' não encontrada.")
    print("       Instale com: pip install networkx")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Constantes — situações do SIGAA
# ─────────────────────────────────────────────────────────────

SITUACOES_APROVADO  = {"APR", "APRN", "DISP", "TRANS", "INCORP", "CUMP"}
SITUACOES_REPROVADO = {"REP", "REPMF", "REPF", "REPN", "REPNF"}
SITUACOES_ANDAMENTO = {"MATR", "REC", "TRANC", "CANC"}


# ─────────────────────────────────────────────────────────────
# 1. LEITURA DO HISTÓRICO ESCOLAR (PDF SIGAA)
# ─────────────────────────────────────────────────────────────

def _normalizar_nome(texto: str) -> str:
    """
    Normaliza nome de disciplina para comparação:
    remove acentos, pontuação, espaços extras e converte para minúsculas.
    """
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-z0-9 ]', '', texto.lower())
    return re.sub(r'\s+', ' ', texto).strip()


def _extrair_texto_pdf(caminho_pdf: str) -> str:
    """Extrai o texto completo de todas as páginas do PDF."""
    caminho = Path(caminho_pdf)
    if not caminho.exists():
        raise FileNotFoundError(f"Histórico escolar não encontrado: {caminho_pdf}")
    with pdfplumber.open(caminho) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def _extrair_semestre_atual(texto: str) -> int | None:
    """
    Extrai o semestre atual do aluno a partir do campo
    'Período Letivo Atual' no histórico SIGAA.
    Retorna 1 (ímpar) ou 2 (par), ou None se não encontrado.
    """
    m = re.search(r"Per[ií]odo Letivo Atual[:\s]+(\d+)", texto)
    return int(m.group(1)) if m else None


def _extrair_disciplinas_historico(texto: str) -> list[dict]:
    """
    Extrai todas as disciplinas cursadas/cursando do histórico SIGAA.

    Formato do PDF SIGAA:
        Nome da Disciplina (codigo_mec)
        ANO.SEM [símbolo] COD_SIGAA  horas CH turma freq nota media SITUACAO

    Retorna lista de dicionários:
        {
          "codigo_sigaa": str,   # ex: "NCC0108"
          "nome_bruto":   str,   # ex: "Produção Textual"
          "situacao":     str,   # ex: "APR"
          "aprovado":     bool
        }
    """
    linhas = texto.split('\n')
    resultado = []

    padrao = re.compile(
        r"^\d{4}\.\d\s+[*&#@§%e]?\s*([A-Z]{2,4}\d{4})\b.*?\b(\d+)\s+(\d+)\s+\d+.*?\b(APR|APRN|DISP|TRANS|INCORP|CUMP|REP|REPMF|REPF|REPN|REPNF|MATR|TRANC|CANC|REC)$"
    )

    for i, linha in enumerate(linhas):
        m = padrao.match(linha.strip())
        if not m:
            continue

        cod_sigaa = m.group(1)
        ch_aula = m.group(2)
        ch_total = m.group(3)
        situacao = m.group(4)

        # Nome está na linha anterior ao código da turma
        nome_bruto = ""
        if i > 0:
            linha_anterior = linhas[i - 1].strip()
            nome_bruto = re.sub(r'\(\d+\).*$', '', linha_anterior).strip()
            nome_bruto = re.sub(
                r'\s*-\s*(SALA|TURMA|PERÍODO|CAMPUS).*$', '',
                nome_bruto, flags=re.IGNORECASE
            ).strip()

        resultado.append({
            "codigo_sigaa": cod_sigaa,
            "nome_bruto":   nome_bruto,
            "situacao":     situacao,
            "aprovado":     situacao in SITUACOES_APROVADO,
            "carga_horaria": int(ch_total)
        })

    return resultado


def ler_historico(caminho_pdf: str) -> tuple[list[str], int | None, list[dict]]:
    """
    Lê o histórico escolar em PDF do SIGAA.

    Parâmetros:
        caminho_pdf: caminho para o PDF do histórico

    Retorno:
        (codigos_aprovados_sigaa, semestre_atual, todas_disciplinas)
            codigos_aprovados_sigaa : lista de códigos SIGAA aprovados
            semestre_atual          : semestre atual do aluno (1 ou 2)
            todas_disciplinas       : lista completa com situação de cada disciplina
    """
    texto = _extrair_texto_pdf(caminho_pdf)
    semestre_atual    = _extrair_semestre_atual(texto)
    todas_disciplinas = _extrair_disciplinas_historico(texto)
    codigos_aprovados = [d['codigo_sigaa'] for d in todas_disciplinas if d['aprovado']]
    return codigos_aprovados, semestre_atual, todas_disciplinas


# ─────────────────────────────────────────────────────────────
# 2. MAPEAMENTO SIGAA → CÓDIGO INTERNO DA GRADE
# ─────────────────────────────────────────────────────────────

def _construir_mapa_sigaa_grade(
    disciplinas_grade: list[dict],
    disciplinas_historico: list[dict]
) -> dict[str, str | None]:
    """
    Mapeia código SIGAA (ex: 'NCC0108') para código interno da grade
    (ex: 'P1_07'), comparando nomes normalizados.

    Trata UCEs dinamicamente associando-as sequencialmente a slots de UCE
    da grade de mesma carga horária.
    """
    # Cria o índice de disciplinas que NÃO são UCEs
    indice_grade = {
        _normalizar_nome(d['nome']): d['codigo']
        for d in disciplinas_grade
        if d['nome'].upper() != 'UCE'
    }

    # Coleta todos os slots de UCE da grade
    uces_grade = [d for d in disciplinas_grade if d['nome'].upper() == 'UCE']
    uces_mapeadas = set()

    mapa = {}
    for disc in disciplinas_historico:
        cod_sigaa = disc['codigo_sigaa']
        if cod_sigaa in mapa:
            continue

        nome_bruto = disc['nome_bruto']
        nome_norm = _normalizar_nome(nome_bruto)

        # Identifica se é UCE
        is_uce = (cod_sigaa.startswith('UCE') or 
                  'uce' in nome_norm or 
                  'unidade curricular de extensao' in nome_norm)

        if is_uce:
            # Associa a um slot de UCE da grade com carga horária compatível
            ch_historico = disc.get('carga_horaria')
            codigo_grade_uce = None
            for uce in uces_grade:
                if uce['codigo'] not in uces_mapeadas and uce['carga_horaria'] == ch_historico:
                    codigo_grade_uce = uce['codigo']
                    uces_mapeadas.add(codigo_grade_uce)
                    break
            
            # Fallback para qualquer slot UCE não mapeado se a carga horária não bater exatamente
            if not codigo_grade_uce:
                for uce in uces_grade:
                    if uce['codigo'] not in uces_mapeadas:
                        codigo_grade_uce = uce['codigo']
                        uces_mapeadas.add(codigo_grade_uce)
                        break

            mapa[cod_sigaa] = codigo_grade_uce
            continue

        # 1. Correspondência exata por nome normalizado
        if nome_norm in indice_grade:
            mapa[cod_sigaa] = indice_grade[nome_norm]
            continue

        # 2. Maior sobreposição de palavras (mínimo 2 em comum)
        melhor, maior_overlap = None, 0
        palavras_hist = set(nome_norm.split())
        for k_grade, v_grade in indice_grade.items():
            overlap = len(palavras_hist & set(k_grade.split()))
            if overlap > maior_overlap and overlap >= 2:
                maior_overlap = overlap
                melhor = v_grade

        mapa[cod_sigaa] = melhor  # None se não encontrou

    return mapa


# ─────────────────────────────────────────────────────────────
# 3. REMOÇÃO DAS APROVADAS DO GRAFO
# ─────────────────────────────────────────────────────────────

def remover_aprovadas_do_grafo(
    G: nx.DiGraph,
    codigos_aprovados_sigaa: list[str],
    disciplinas_grade: list[dict],
    disciplinas_historico: list[dict]
) -> tuple[nx.DiGraph, list[str], list[str]]:
    """
    Remove do grafo (construído pelo grafo.py da Pessoa 1) todos os
    nós correspondentes a disciplinas já aprovadas pelo aluno.

    Ao remover um nó, o NetworkX remove automaticamente todas as
    arestas que partem dele — o que equivale a satisfazer o
    pré-requisito para as disciplinas dependentes.

    Parâmetros:
        G                      : grafo dirigido construído por grafo.py
        codigos_aprovados_sigaa: lista de códigos SIGAA aprovados
        disciplinas_grade      : lista de disciplinas da grade (grade.json)
        disciplinas_historico  : lista extraída de ler_historico()

    Retorno:
        (G, codigos_removidos, codigos_nao_mapeados)
            G                   : grafo modificado (apenas pendentes)
            codigos_removidos   : códigos internos efetivamente removidos
            codigos_nao_mapeados: códigos SIGAA sem correspondência na grade
    """
    mapa = _construir_mapa_sigaa_grade(disciplinas_grade, disciplinas_historico)

    codigos_removidos    = []
    codigos_nao_mapeados = []

    for cod_sigaa in codigos_aprovados_sigaa:
        codigo_grade = mapa.get(cod_sigaa)
        if codigo_grade is None:
            codigos_nao_mapeados.append(cod_sigaa)
            continue
        if G.has_node(codigo_grade):
            G.remove_node(codigo_grade)
            codigos_removidos.append(codigo_grade)

    return G, codigos_removidos, codigos_nao_mapeados


# ─────────────────────────────────────────────────────────────
# 4. FUNÇÃO PRINCIPAL (orquestra tudo usando grafo.py)
# ─────────────────────────────────────────────────────────────

def carregar_dados_entrada(
    caminho_grade: str,
    caminho_historico: str,
    max_disciplinas: int = 6
) -> tuple[list[dict], nx.DiGraph, int]:
    """
    Função principal da Pessoa 2.
    Usa grafo.py (Pessoa 1) para construir o grafo e depois o atualiza
    com base no histórico escolar do aluno.

    Parâmetros:
        caminho_grade    : caminho para grade.json
        caminho_historico: caminho para o PDF do histórico SIGAA
        max_disciplinas  : limite de disciplinas por semestre (5–7)

    Retorno:
        (disciplinas_grade, G_pendente, semestre_atual)
            disciplinas_grade: lista completa das disciplinas da grade
            G_pendente       : grafo com apenas disciplinas pendentes
            semestre_atual   : semestre atual do aluno (1 ou 2)
    """
    if not (5 <= max_disciplinas <= 7):
        raise ValueError(f"max_disciplinas deve ser entre 5 e 7, recebido: {max_disciplinas}")

    # Importa grafo.py da Pessoa 1
    try:
        from grafo import carregar_grade, construir_grafo
    except ImportError:
        print("[ERRO] grafo.py não encontrado. Certifique-se de que está na mesma pasta.")
        sys.exit(1)

    print("=" * 60)
    print("LEITURA E PREPARAÇÃO DOS DADOS")
    print("=" * 60)

    # 1. Carrega grade e constrói grafo (Pessoa 1)
    print(f"\n[1/3] Carregando grade e construindo grafo: {caminho_grade}")
    disciplinas_grade = carregar_grade(caminho_grade)
    G = construir_grafo(disciplinas_grade)
    print(f"      {G.number_of_nodes()} nós | {G.number_of_edges()} arestas | "
          f"DAG válido: {nx.is_directed_acyclic_graph(G)}")

    # 2. Lê histórico escolar
    print(f"\n[2/3] Lendo histórico escolar: {caminho_historico}")
    aprovadas_sigaa, semestre_atual, todas = ler_historico(caminho_historico)
    print(f"      Semestre atual do aluno  : {semestre_atual}")
    print(f"      Disciplinas aprovadas    : {len(aprovadas_sigaa)}")

    # 3. Remove aprovadas do grafo
    print("\n[3/3] Removendo disciplinas aprovadas do grafo...")
    G_pendente, removidos, nao_mapeados = remover_aprovadas_do_grafo(
        G, aprovadas_sigaa, disciplinas_grade, todas
    )
    print(f"      Removidas : {len(removidos)}")
    print(f"      Pendentes : {G_pendente.number_of_nodes()}")

    if nao_mapeados:
        print(f"\n[AVISO] {len(nao_mapeados)} código(s) SIGAA sem correspondência na grade "
              "(optativas, eletivas ou equivalências externas):")
        for c in nao_mapeados:
            print(f"         - {c}")

    _imprimir_resumo(G_pendente, semestre_atual, max_disciplinas)

    return disciplinas_grade, G_pendente, semestre_atual


def _imprimir_resumo(G: nx.DiGraph, semestre_atual: int | None, max_disc: int) -> None:
    """Imprime resumo do estado do grafo para o planejamento."""
    disponiveis = [n for n in G.nodes() if G.in_degree(n) == 0]

    print("\n" + "=" * 60)
    print("RESUMO PARA O PLANEJAMENTO")
    print("=" * 60)
    print(f"  Semestre atual do aluno : {semestre_atual}")
    print(f"  Máx. disciplinas/sem.   : {max_disc}")
    print(f"  Disciplinas pendentes   : {G.number_of_nodes()}")
    print(f"  Relações de pré-req.    : {G.number_of_edges()}")
    print(f"  Disponíveis agora       : {len(disponiveis)}")

    if disponiveis:
        print("\n  Disciplinas disponíveis para alocação imediata:")
        for cod in disponiveis:
            d = G.nodes[cod]
            oferta = "ímpar" if d['semestre_oferta'] == 1 else "par"
            print(f"    [{cod}] {d['nome']} (semestre {oferta}, {d['carga_horaria']}h)")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────
# EXECUÇÃO DIRETA
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Leitura do histórico e atualização do grafo para planejamento acadêmico."
    )
    parser.add_argument("--grade",     default="grade.json",
                        help="Caminho para grade.json (padrão: grade.json)")
    parser.add_argument("--historico", required=True,
                        help="Caminho para o PDF do histórico escolar SIGAA")
    parser.add_argument("--max",       type=int, default=6, choices=[5, 6, 7],
                        help="Máx. disciplinas por semestre (padrão: 6)")
    args = parser.parse_args()

    carregar_dados_entrada(
        caminho_grade=args.grade,
        caminho_historico=args.historico,
        max_disciplinas=args.max
    )