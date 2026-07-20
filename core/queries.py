"""
Funções de leitura e escrita no banco (regra de negócio).
Nenhuma página deve montar SQL diretamente — tudo passa por aqui.
"""

import psycopg2
from datetime import date

import pandas as pd

from core.database import get_conn, registrar_lancamento


def df(query, params=()):
    conn = get_conn()
    result = pd.read_sql_query(query.replace("?", "%s"), conn.raw, params=params)
    conn.close()
    return result


# ----------------------------------------------------------------------
# LIGAS
# ----------------------------------------------------------------------

def lista_ligas():
    return df("SELECT id, nome FROM ligas ORDER BY nome")


def lista_ligas_com_totais():
    return df(
        """
        SELECT l.nome AS "Liga", l.descricao AS "Descrição",
               COUNT(DISTINCT c.id) AS "Clubes",
               COUNT(DISTINCT j.id) AS "Jogadores"
        FROM ligas l
        LEFT JOIN clubes c ON c.liga_id = l.id
        LEFT JOIN jogadores j ON j.liga_id = l.id
        GROUP BY l.id
        ORDER BY l.nome
        """
    )


def criar_liga(nome, descricao=""):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO ligas (nome, descricao) VALUES (?,?)", (nome.strip(), descricao.strip()))
        conn.commit()
    except psycopg2.IntegrityError:
        raise
    finally:
        conn.close()


def editar_liga(liga_id, nome, descricao=""):
    conn = get_conn()
    try:
        conn.execute("UPDATE ligas SET nome = ?, descricao = ? WHERE id = ?", (nome.strip(), descricao.strip(), liga_id))
        conn.commit()
    except psycopg2.IntegrityError:
        raise
    finally:
        conn.close()


# ----------------------------------------------------------------------
# CLUBES
# ----------------------------------------------------------------------

def lista_clubes(liga_id):
    return df("SELECT id, nome FROM clubes WHERE liga_id = ? ORDER BY nome", (liga_id,))


def lista_clubes_dashboard(liga_id):
    return df(
        'SELECT nome AS "Clube", tecnico AS "Técnico", saldo AS "Saldo" FROM clubes WHERE liga_id = ? ORDER BY saldo DESC',
        (liga_id,),
    )


def lista_clubes_completo(liga_id):
    return df(
        'SELECT id AS "ID", nome AS "Nome", tecnico AS "Técnico", saldo AS "Saldo" FROM clubes WHERE liga_id = ? ORDER BY nome',
        (liga_id,),
    )


def lista_clubes_por_folha_salarial(liga_id):
    """Folha salarial (soma dos salários do elenco) de cada clube, do mais
    caro para o mais barato — é o que define o 'time mais caro da liga'."""
    return df(
        """
        SELECT c.nome AS "Clube", COALESCE(SUM(j.salario), 0) AS "Folha Salarial"
        FROM clubes c
        LEFT JOIN jogadores j ON j.clube_id = c.id
        WHERE c.liga_id = ?
        GROUP BY c.id, c.nome
        ORDER BY "Folha Salarial" DESC
        """,
        (liga_id,),
    )


def cobrar_salarios(liga_id):
    """Desconta do saldo de cada clube a soma dos salários do seu elenco atual,
    lançando um débito no financeiro para cada clube com folha > 0.
    Retorna quantos clubes tiveram salário cobrado."""
    conn = get_conn()
    linhas = conn.execute(
        """
        SELECT c.id, COALESCE(SUM(j.salario), 0)
        FROM clubes c
        LEFT JOIN jogadores j ON j.clube_id = c.id
        WHERE c.liga_id = ?
        GROUP BY c.id
        """,
        (liga_id,),
    ).fetchall()

    cobrados = 0
    for clube_id, total in linhas:
        total = float(total or 0)
        if total > 0:
            registrar_lancamento(conn, clube_id, "Pagamento de salários", -total, "Salário")
            cobrados += 1

    conn.commit()
    conn.close()
    return cobrados


def criar_clube(nome, tecnico, saldo_inicial, liga_id):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO clubes (nome, tecnico, saldo, liga_id) VALUES (?,?,?,?)",
            (nome.strip(), tecnico.strip(), saldo_inicial, liga_id),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        raise
    finally:
        conn.close()


def ajustar_saldo_clube(clube_id, valor_ajuste, motivo):
    conn = get_conn()
    registrar_lancamento(conn, clube_id, motivo or "Ajuste manual", valor_ajuste, "Ajuste")
    conn.commit()
    conn.close()


def editar_clube(clube_id, nome, tecnico, saldo):
    """Edita nome/técnico/saldo do clube diretamente (sem passar pelo livro financeiro —
    use isso para correções de cadastro, não para movimentações do dia a dia)."""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE clubes SET nome = ?, tecnico = ?, saldo = ? WHERE id = ?",
            (nome.strip(), tecnico.strip(), saldo, clube_id),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        raise
    finally:
        conn.close()


def deletar_clube(clube_id):
    """Apaga o clube. Jogadores desse clube ficam 'Sem clube' (não são apagados).
    Histórico financeiro, patrocínios e transferências ligados a esse clube_id
    também são removidos, já que fariam referência a um clube inexistente."""
    conn = get_conn()
    conn.execute("UPDATE jogadores SET clube_id = NULL WHERE clube_id = ?", (clube_id,))
    conn.execute("DELETE FROM financeiro WHERE clube_id = ?", (clube_id,))
    conn.execute("DELETE FROM patrocinios WHERE clube_id = ?", (clube_id,))
    conn.execute(
        "DELETE FROM transferencias WHERE clube_origem_id = ? OR clube_destino_id = ?",
        (clube_id, clube_id),
    )
    conn.execute("DELETE FROM clubes WHERE id = ?", (clube_id,))
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# JOGADORES
# ----------------------------------------------------------------------

def lista_jogadores_da_liga(liga_id):
    return df(
        """
        SELECT j.id AS "ID", j.nome AS "Nome", j.posicao AS "Posição", j.overall AS "Overall",
               j.valor_mercado AS "Valor de Mercado", j.salario AS "Salário",
               COALESCE(c.nome, 'Sem clube') AS "Clube"
        FROM jogadores j
        LEFT JOIN clubes c ON c.id = j.clube_id
        WHERE j.liga_id = ?
        """,
        (liga_id,),
    )


def lista_jogadores_simples(liga_id):
    return df("SELECT id, nome, clube_id FROM jogadores WHERE liga_id = ?", (liga_id,))


def criar_jogador(nome, posicao, overall, valor_mercado, salario, clube_id, liga_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO jogadores (nome, posicao, overall, valor_mercado, salario, clube_id, liga_id) VALUES (?,?,?,?,?,?,?)",
        (nome.strip(), posicao, overall, valor_mercado, salario, clube_id, liga_id),
    )
    conn.commit()
    conn.close()


def editar_jogador(jogador_id, nome, posicao, overall, valor_mercado, salario, clube_id):
    conn = get_conn()
    conn.execute(
        "UPDATE jogadores SET nome = ?, posicao = ?, overall = ?, valor_mercado = ?, salario = ?, clube_id = ? WHERE id = ?",
        (nome.strip(), posicao, overall, valor_mercado, salario, clube_id, jogador_id),
    )
    conn.commit()
    conn.close()


def buscar_jogador(jogador_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, nome, posicao, overall, valor_mercado, salario, clube_id FROM jogadores WHERE id = ?",
        (jogador_id,),
    ).fetchone()
    conn.close()
    return row


# ----------------------------------------------------------------------
# TRANSFERÊNCIAS
# ----------------------------------------------------------------------

def registrar_transferencia(jogador_id, jogador_nome, clube_origem_id, destino_id, clube_destino_nome, valor):
    """Registra a transferência. Levanta ValueError se o clube de destino não
    tiver saldo suficiente para pagar o valor da transferência."""
    # clube_origem_id costuma vir de uma coluna do pandas (numpy.int64/float64 quando
    # há valores nulos misturados) — o driver psycopg2 não aceita esses tipos, então
    # normalizamos para int/None nativos do Python logo no início.
    clube_origem_id = int(clube_origem_id) if pd.notna(clube_origem_id) else None
    jogador_id = int(jogador_id)
    destino_id = int(destino_id)
    valor = float(valor)

    conn = get_conn()

    if valor > 0:
        saldo_destino = conn.execute("SELECT saldo FROM clubes WHERE id = ?", (destino_id,)).fetchone()[0]
        if saldo_destino < valor:
            conn.close()
            raise ValueError(
                f"{clube_destino_nome} não tem saldo suficiente para essa transferência "
                f"(saldo atual: R$ {saldo_destino:,.2f}, valor: R$ {valor:,.2f})."
            )

    conn.execute(
        "INSERT INTO transferencias (jogador_id, clube_origem_id, clube_destino_id, valor, data) VALUES (?,?,?,?,?)",
        (jogador_id, clube_origem_id, destino_id, valor, date.today().isoformat()),
    )
    conn.execute("UPDATE jogadores SET clube_id = ? WHERE id = ?", (destino_id, jogador_id))

    if clube_origem_id is not None and valor > 0:
        registrar_lancamento(conn, clube_origem_id, f"Venda de {jogador_nome}", valor, "Transferência - venda")
    if valor > 0:
        registrar_lancamento(conn, destino_id, f"Compra de {jogador_nome}", -valor, "Transferência - compra")

    conn.commit()
    conn.close()


def buscar_transferencia(transferencia_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, jogador_id, clube_origem_id, clube_destino_id, valor FROM transferencias WHERE id = ?",
        (transferencia_id,),
    ).fetchone()
    conn.close()
    return row


def cancelar_transferencia(transferencia_id):
    """Anula uma transferência: devolve o jogador ao clube de origem, estorna o
    valor nos saldos (com lançamento de estorno no financeiro, para manter o
    histórico) e apaga o registro da transferência."""
    conn = get_conn()
    t = conn.execute(
        "SELECT jogador_id, clube_origem_id, clube_destino_id, valor FROM transferencias WHERE id = ?",
        (transferencia_id,),
    ).fetchone()
    if not t:
        conn.close()
        return
    jogador_id, clube_origem_id, clube_destino_id, valor = t
    jogador_nome = conn.execute("SELECT nome FROM jogadores WHERE id = ?", (jogador_id,)).fetchone()[0]

    # Se o clube de origem guardado na transferência não existir mais (dado
    # inconsistente de uma versão antiga, ou clube que não existe de fato),
    # o jogador volta como "Sem clube" em vez de travar com erro de FK.
    if clube_origem_id is not None:
        existe_origem = conn.execute("SELECT 1 FROM clubes WHERE id = ?", (clube_origem_id,)).fetchone()
        if not existe_origem:
            clube_origem_id = None

    if valor and valor > 0:
        if clube_origem_id is not None:
            registrar_lancamento(conn, clube_origem_id, f"Estorno - transferência de {jogador_nome} anulada", -valor, "Estorno")
        registrar_lancamento(conn, clube_destino_id, f"Estorno - transferência de {jogador_nome} anulada", valor, "Estorno")

    conn.execute("UPDATE jogadores SET clube_id = ? WHERE id = ?", (clube_origem_id, jogador_id))
    conn.execute("DELETE FROM transferencias WHERE id = ?", (transferencia_id,))
    conn.commit()
    conn.close()


def editar_valor_transferencia(transferencia_id, novo_valor):
    """Corrige o valor de uma transferência já registrada: estorna o efeito
    financeiro do valor antigo e aplica o novo valor nos saldos."""
    conn = get_conn()
    t = conn.execute(
        "SELECT jogador_id, clube_origem_id, clube_destino_id, valor FROM transferencias WHERE id = ?",
        (transferencia_id,),
    ).fetchone()
    if not t:
        conn.close()
        return
    jogador_id, clube_origem_id, clube_destino_id, valor_antigo = t
    jogador_nome = conn.execute("SELECT nome FROM jogadores WHERE id = ?", (jogador_id,)).fetchone()[0]

    if clube_origem_id is not None:
        existe_origem = conn.execute("SELECT 1 FROM clubes WHERE id = ?", (clube_origem_id,)).fetchone()
        if not existe_origem:
            clube_origem_id = None

    if novo_valor > 0:
        saldo_destino = conn.execute("SELECT saldo FROM clubes WHERE id = ?", (clube_destino_id,)).fetchone()[0]
        saldo_destino_sem_transf_antiga = saldo_destino + (valor_antigo or 0)
        if saldo_destino_sem_transf_antiga < novo_valor:
            conn.close()
            raise ValueError("Clube de destino não tem saldo suficiente para o novo valor da transferência.")

    if valor_antigo and valor_antigo > 0:
        if clube_origem_id is not None:
            registrar_lancamento(conn, clube_origem_id, f"Ajuste de valor - transferência de {jogador_nome}", -valor_antigo, "Ajuste")
        registrar_lancamento(conn, clube_destino_id, f"Ajuste de valor - transferência de {jogador_nome}", valor_antigo, "Ajuste")

    if novo_valor and novo_valor > 0:
        if clube_origem_id is not None:
            registrar_lancamento(conn, clube_origem_id, f"Ajuste de valor - transferência de {jogador_nome}", novo_valor, "Ajuste")
        registrar_lancamento(conn, clube_destino_id, f"Ajuste de valor - transferência de {jogador_nome}", -novo_valor, "Ajuste")

    conn.execute("UPDATE transferencias SET valor = ? WHERE id = ?", (novo_valor, transferencia_id))
    conn.commit()
    conn.close()


def historico_transferencias(liga_id):
    return df(
        """
        SELECT t.id AS "ID", t.data AS "Data", j.nome AS "Jogador",
               COALESCE(co.nome, 'Sem clube') AS "Origem",
               cd.nome AS "Destino", t.valor AS "Valor"
        FROM transferencias t
        JOIN jogadores j ON j.id = t.jogador_id
        LEFT JOIN clubes co ON co.id = t.clube_origem_id
        JOIN clubes cd ON cd.id = t.clube_destino_id
        WHERE j.liga_id = ?
        ORDER BY t.id DESC
        """,
        (liga_id,),
    )


# ----------------------------------------------------------------------
# PATROCÍNIOS
# ----------------------------------------------------------------------

def lancar_patrocinio(clube_id, patrocinador, valor, tipo):
    conn = get_conn()
    conn.execute(
        "INSERT INTO patrocinios (clube_id, patrocinador, valor, tipo, data) VALUES (?,?,?,?,?)",
        (clube_id, patrocinador.strip(), valor, tipo, date.today().isoformat()),
    )
    registrar_lancamento(conn, clube_id, f"Patrocínio: {patrocinador}", valor, "Patrocínio")
    conn.commit()
    conn.close()


def buscar_patrocinio(patrocinio_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, clube_id, patrocinador, valor, tipo FROM patrocinios WHERE id = ?", (patrocinio_id,)
    ).fetchone()
    conn.close()
    return row


def editar_patrocinio(patrocinio_id, patrocinador, novo_valor, tipo):
    """Corrige patrocinador/valor/tipo de um patrocínio já lançado, estornando
    o efeito do valor antigo no saldo e aplicando o novo (com rastro no financeiro)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT clube_id, patrocinador, valor FROM patrocinios WHERE id = ?", (patrocinio_id,)
    ).fetchone()
    if not row:
        conn.close()
        return
    clube_id, patrocinador_antigo, valor_antigo = row

    existe_clube = conn.execute("SELECT 1 FROM clubes WHERE id = ?", (clube_id,)).fetchone()
    if existe_clube:
        registrar_lancamento(conn, clube_id, f"Ajuste de patrocínio: {patrocinador_antigo}", -valor_antigo, "Ajuste")
        registrar_lancamento(conn, clube_id, f"Ajuste de patrocínio: {patrocinador}", novo_valor, "Ajuste")

    conn.execute(
        "UPDATE patrocinios SET patrocinador = ?, valor = ?, tipo = ? WHERE id = ?",
        (patrocinador.strip(), novo_valor, tipo, patrocinio_id),
    )
    conn.commit()
    conn.close()


def deletar_patrocinio(patrocinio_id):
    """Apaga o patrocínio e estorna o valor do saldo do clube (com lançamento
    de estorno no financeiro, para manter o histórico)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT clube_id, patrocinador, valor FROM patrocinios WHERE id = ?", (patrocinio_id,)
    ).fetchone()
    if not row:
        conn.close()
        return
    clube_id, patrocinador, valor = row

    existe_clube = conn.execute("SELECT 1 FROM clubes WHERE id = ?", (clube_id,)).fetchone()
    if existe_clube:
        registrar_lancamento(conn, clube_id, f"Estorno - patrocínio removido: {patrocinador}", -valor, "Estorno")

    conn.execute("DELETE FROM patrocinios WHERE id = ?", (patrocinio_id,))
    conn.commit()
    conn.close()


def historico_patrocinios(liga_id):
    return df(
        """
        SELECT p.id AS "ID", p.data AS "Data", c.nome AS "Clube", p.patrocinador AS "Patrocinador",
               p.tipo AS "Tipo", p.valor AS "Valor"
        FROM patrocinios p
        JOIN clubes c ON c.id = p.clube_id
        WHERE c.liga_id = ?
        ORDER BY p.id DESC
        """,
        (liga_id,),
    )


# ----------------------------------------------------------------------
# FINANCEIRO
# ----------------------------------------------------------------------

def historico_financeiro(liga_id, limite=None):
    query = """
        SELECT f.data AS "Data", c.nome AS "Clube", f.descricao AS "Descrição",
               f.categoria AS "Categoria", f.valor AS "Valor"
        FROM financeiro f
        JOIN clubes c ON c.id = f.clube_id
        WHERE c.liga_id = ?
        ORDER BY f.id DESC
    """
    if limite:
        query += f" LIMIT {int(limite)}"
    return df(query, (liga_id,))


# ----------------------------------------------------------------------
# USUÁRIOS (login/permissões)
# ----------------------------------------------------------------------

def lista_usuarios():
    return df(
        """
        SELECT u.id AS "ID", u.usuario AS "Usuário", u.papel AS "Papel",
               COALESCE(c.nome, '—') AS "Clube", u.clube_id AS clube_id
        FROM usuarios u
        LEFT JOIN clubes c ON c.id = u.clube_id
        ORDER BY u.papel, u.usuario
        """
    )


def criar_usuario(usuario, senha, papel, clube_id=None):
    """Cria um usuário. Para papel='visualizador', clube_id deve ser o clube
    ao qual ele terá acesso (None = ainda sem clube vinculado)."""
    from core.database import _hash_senha

    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO usuarios (usuario, senha_hash, papel, clube_id) VALUES (?,?,?,?)",
            (usuario.strip(), _hash_senha(senha), papel, clube_id),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        raise
    finally:
        conn.close()


def editar_vinculo_usuario(usuario_id, clube_id):
    """Troca o clube ao qual um visualizador está vinculado."""
    conn = get_conn()
    conn.execute("UPDATE usuarios SET clube_id = ? WHERE id = ?", (clube_id, usuario_id))
    conn.commit()
    conn.close()


def redefinir_senha_usuario(usuario_id, nova_senha):
    from core.database import _hash_senha

    conn = get_conn()
    conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (_hash_senha(nova_senha), usuario_id))
    conn.commit()
    conn.close()


def deletar_usuario(usuario_id):
    conn = get_conn()
    conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# NEGOCIAÇÕES (Compra / Troca) — suportam transferência entre ligas
# e aplicam a trava de 2 negociações por clube por dia
# ----------------------------------------------------------------------

LIMITE_NEGOCIACOES_POR_DIA = 2


def lista_clubes_todas_ligas():
    """Todos os clubes de todas as ligas, com o nome da liga junto —
    usado no seletor de clubes quando a negociação é entre ligas."""
    return df(
        """
        SELECT c.id AS "id", c.nome AS "nome", c.liga_id AS "liga_id", l.nome AS "liga_nome"
        FROM clubes c
        JOIN ligas l ON l.id = c.liga_id
        ORDER BY l.nome, c.nome
        """
    )


def lista_jogadores_por_clube(clube_id):
    """Jogadores de UM clube específico, independente da liga em que o
    clube está — necessário para montar negociações entre ligas."""
    return df(
        'SELECT id AS "id", nome AS "nome" FROM jogadores WHERE clube_id = ? ORDER BY nome',
        (clube_id,),
    )


def contar_negociacoes_hoje(clube_id):
    """Quantas negociações (compra ou troca) esse clube já participou hoje,
    seja como clube_a ou clube_b."""
    hoje = date.today().isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) FROM negociacoes WHERE data = ? AND (clube_a_id = ? OR clube_b_id = ?)",
        (hoje, clube_id, clube_id),
    ).fetchone()
    conn.close()
    return row[0]


def registrar_negociacao(tipo, clube_a_id, clube_b_id, movimentos, valor_compensacao=0, clube_pagador_id=None, clube_recebedor_id=None):
    """Registra uma negociação (compra ou troca) entre dois clubes — inclusive
    de ligas diferentes.

    tipo: 'compra' ou 'troca'
    clube_a_id / clube_b_id: os dois clubes envolvidos (para compra: vendedor e comprador)
    movimentos: lista de tuplas (jogador_id, clube_origem_id, clube_destino_id) —
                um item por jogador que muda de clube nesta negociação
    valor_compensacao: valor pago por clube_pagador_id a clube_recebedor_id (>= 0)
    clube_pagador_id / clube_recebedor_id: só usados se valor_compensacao > 0

    Aplica a trava de LIMITE_NEGOCIACOES_POR_DIA por clube (considerando os
    dois clubes da negociação) e move o(s) jogador(es) — inclusive de liga,
    permitindo transferências entre ligas diferentes.
    """
    if not movimentos:
        raise ValueError("Informe ao menos um jogador na negociação.")

    for clube_id in {int(clube_a_id), int(clube_b_id)}:
        usadas_hoje = contar_negociacoes_hoje(clube_id)
        if usadas_hoje >= LIMITE_NEGOCIACOES_POR_DIA:
            nome_df = df('SELECT nome AS "nome" FROM clubes WHERE id = ?', (clube_id,))
            nome_clube = nome_df.iloc[0]["nome"] if not nome_df.empty else f"clube #{clube_id}"
            raise ValueError(
                f"O clube '{nome_clube}' já atingiu o limite de {LIMITE_NEGOCIACOES_POR_DIA} "
                "transferências hoje. Tente novamente amanhã."
            )

    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO negociacoes (tipo, clube_a_id, clube_b_id, valor_compensacao, data) VALUES (?,?,?,?,?) RETURNING id",
            (tipo, clube_a_id, clube_b_id, valor_compensacao, date.today().isoformat()),
        )
        negociacao_id = cur.fetchone()[0]

        for jogador_id, origem_id, destino_id in movimentos:
            conn.execute(
                "INSERT INTO negociacao_jogadores (negociacao_id, jogador_id, clube_origem_id, clube_destino_id) VALUES (?,?,?,?)",
                (negociacao_id, jogador_id, origem_id, destino_id),
            )
            # Move o jogador de clube e TAMBÉM de liga (herda a liga do clube de destino) —
            # é isso que permite a transferência funcionar entre ligas diferentes.
            liga_row = conn.execute("SELECT liga_id FROM clubes WHERE id = ?", (destino_id,)).fetchone()
            nova_liga_id = liga_row[0] if liga_row else None
            conn.execute(
                "UPDATE jogadores SET clube_id = ?, liga_id = ? WHERE id = ?",
                (destino_id, nova_liga_id, jogador_id),
            )

        if valor_compensacao and valor_compensacao > 0 and clube_pagador_id and clube_recebedor_id:
            registrar_lancamento(conn, clube_pagador_id, f"Negociação #{negociacao_id} ({tipo}) — pagamento", -valor_compensacao, "Transferência")
            registrar_lancamento(conn, clube_recebedor_id, f"Negociação #{negociacao_id} ({tipo}) — recebimento", valor_compensacao, "Transferência")

        conn.commit()
        return negociacao_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def historico_negociacoes(liga_id):
    """Negociações (compra/troca) que envolvem pelo menos um clube desta liga —
    inclusive as que foram feitas com um clube de outra liga."""
    return df(
        """
        SELECT n.id AS "ID", n.tipo AS "Tipo", n.data AS "Data",
               ca.nome AS "Clube A", la.nome AS "Liga A",
               cb.nome AS "Clube B", lb.nome AS "Liga B",
               n.valor_compensacao AS "Valor"
        FROM negociacoes n
        JOIN clubes ca ON ca.id = n.clube_a_id
        JOIN clubes cb ON cb.id = n.clube_b_id
        LEFT JOIN ligas la ON la.id = ca.liga_id
        LEFT JOIN ligas lb ON lb.id = cb.liga_id
        WHERE ca.liga_id = ? OR cb.liga_id = ?
        ORDER BY n.id DESC
        """,
        (liga_id, liga_id),
    )


def detalhes_negociacao(negociacao_id):
    """Lista os jogadores movimentados dentro de uma negociação específica."""
    return df(
        """
        SELECT j.nome AS "Jogador", co.nome AS "Saiu de", cd.nome AS "Foi para"
        FROM negociacao_jogadores nj
        JOIN jogadores j ON j.id = nj.jogador_id
        LEFT JOIN clubes co ON co.id = nj.clube_origem_id
        LEFT JOIN clubes cd ON cd.id = nj.clube_destino_id
        WHERE nj.negociacao_id = ?
        ORDER BY nj.id
        """,
        (negociacao_id,),
    )