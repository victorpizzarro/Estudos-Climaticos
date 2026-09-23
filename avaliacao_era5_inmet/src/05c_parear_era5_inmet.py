from pathlib import Path

import duckdb
import pandas as pd

from config import (
    PROJECT_DIR,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ANO_INICIAL = 2000
ANO_FINAL = 2025


INMET_DIR = (
    PROJECT_DIR
    / "data"
    / "interim"
    / "inmet"
    / "automaticas"
)


ERA5_DIR = (
    PROJECT_DIR
    / "data"
    / "interim"
    / "era5"
    / "pontos_inmet"
)


MATCHES_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "matches"
)


ARQUIVO_MATCHES = (
    MATCHES_DIR
    / "inmet_era5_estacao_ano.csv"
)


PARES_DIR = (
    MATCHES_DIR
    / "horarios"
)


PARES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ARQUIVO_RESUMO = (
    TABLES_DIR
    / "resumo_pareamento_temporal_era5_inmet.csv"
)


# ==========================================================
# AUXILIAR PARA CAMINHOS SQL
# ==========================================================

def sql_path(caminho):
    """
    Escapa caminho para uso dentro de string SQL.
    """

    return str(
        caminho.resolve()
    ).replace(
        "'",
        "''",
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)
print("PAREAMENTO HORÁRIO ERA5 × INMET")
print("=" * 90)

print(
    "\nDefinição do erro:"
)

print(
    "erro = ERA5 - INMET"
)

print(
    "\nPortanto:"
)

print(
    "erro < 0  → ERA5 subestimou"
)

print(
    "erro > 0  → ERA5 superestimou"
)


# ==========================================================
# 1. VERIFICAR ARQUIVO DE MAPEAMENTO
# ==========================================================

if not ARQUIVO_MATCHES.exists():

    raise FileNotFoundError(
        f"Pareamento espacial não encontrado:\n"
        f"{ARQUIVO_MATCHES}"
    )


# ==========================================================
# 2. CONEXÃO DUCKDB
# ==========================================================

con = duckdb.connect(
    database=":memory:"
)


# Limitar uso de memória evita que uma consulta
# especialmente animada tente dominar o computador.
con.execute(
    "SET memory_limit = '4GB'"
)


# DuckDB pode usar vários threads.
con.execute(
    "SET threads = 4"
)


# ==========================================================
# 3. CARREGAR MAPEAMENTO
# ==========================================================

print("\n" + "=" * 90)
print("CARREGANDO PAREAMENTO ESPACIAL")
print("=" * 90)


matches_sql = sql_path(
    ARQUIVO_MATCHES
)


con.execute(
    f"""
    CREATE TABLE matches AS

    SELECT
        CAST(ano AS INTEGER) AS ano,
        CAST(codigo AS VARCHAR) AS codigo,
        CAST(grid_index AS INTEGER) AS grid_index,
        CAST(estacao AS VARCHAR) AS estacao,
        CAST(uf AS VARCHAR) AS uf,
        CAST(regiao AS VARCHAR) AS regiao,
        CAST(latitude_inmet AS DOUBLE) AS latitude_inmet,
        CAST(longitude_inmet AS DOUBLE) AS longitude_inmet,
        CAST(latitude_era5 AS DOUBLE) AS latitude_era5,
        CAST(longitude_era5 AS DOUBLE) AS longitude_era5,
        CAST(distancia_centro_km AS DOUBLE)
            AS distancia_centro_km,
        CAST(observacoes_inmet AS BIGINT)
            AS observacoes_inmet

    FROM read_csv_auto(
        '{matches_sql}',
        header=true
    )
    """
)


total_matches = con.execute(
    """
    SELECT COUNT(*)
    FROM matches
    """
).fetchone()[0]


print(
    f"\nRegistros estação-ano carregados: "
    f"{total_matches:,}"
)


# ==========================================================
# 4. PROCESSAR ANO POR ANO
# ==========================================================

resumo = []

tudo_ok = True


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    print("\n" + "=" * 90)
    print(f"ANO {ano}")
    print("=" * 90)


    inmet_file = (
        INMET_DIR
        / f"inmet_{ano}.parquet"
    )


    era5_file = (
        ERA5_DIR
        / f"era5_pontos_inmet_{ano}.parquet"
    )


    saida_file = (
        PARES_DIR
        / f"era5_inmet_pares_{ano}.parquet"
    )


    if not inmet_file.exists():

        raise FileNotFoundError(
            f"INMET ausente:\n"
            f"{inmet_file}"
        )


    if not era5_file.exists():

        raise FileNotFoundError(
            f"ERA5 ausente:\n"
            f"{era5_file}"
        )


    if saida_file.exists():

        print(
            "\nRemovendo saída anterior:"
        )

        print(
            saida_file
        )

        saida_file.unlink()


    inmet_sql = sql_path(
        inmet_file
    )


    era5_sql = sql_path(
        era5_file
    )


    saida_sql = sql_path(
        saida_file
    )


    # ======================================================
    # 4.1 ESTAÇÕES/CÉLULAS DO ANO
    # ======================================================

    estacoes_ano = con.execute(
        f"""
        SELECT COUNT(*)
        FROM matches
        WHERE ano = {ano}
        """
    ).fetchone()[0]


    celulas_ano = con.execute(
        f"""
        SELECT COUNT(
            DISTINCT grid_index
        )
        FROM matches
        WHERE ano = {ano}
        """
    ).fetchone()[0]


    print(
        f"\nEstações elegíveis: "
        f"{estacoes_ano:,}"
    )


    print(
        f"Células ERA5: "
        f"{celulas_ano:,}"
    )


    # ======================================================
    # 4.2 VERIFICAR DUPLICADOS ERA5
    # ======================================================

    duplicados_era5 = con.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT
                datetime_utc,
                grid_index,
                COUNT(*) AS n

            FROM read_parquet(
                '{era5_sql}'
            )

            GROUP BY
                datetime_utc,
                grid_index

            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]


    if duplicados_era5 > 0:

        raise RuntimeError(
            f"{ano}: ERA5 contém "
            f"{duplicados_era5:,} "
            "chaves horário/célula duplicadas."
        )


    # ======================================================
    # 4.3 DUPLICADOS INMET
    # ======================================================

    duplicados_inmet = con.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT
                codigo,
                datetime_utc,
                COUNT(*) AS n

            FROM read_parquet(
                '{inmet_sql}'
            )

            GROUP BY
                codigo,
                datetime_utc

            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]


    if duplicados_inmet > 0:

        raise RuntimeError(
            f"{ano}: INMET contém "
            f"{duplicados_inmet:,} "
            "chaves estação/hora duplicadas."
        )


    # ======================================================
    # 4.4 QUANTAS OBSERVAÇÕES INMET SÃO ELEGÍVEIS?
    # ======================================================

    inmet_elegiveis = con.execute(
        f"""
        SELECT COUNT(*)

        FROM read_parquet(
            '{inmet_sql}'
        ) AS i

        INNER JOIN matches AS m

            ON i.codigo = m.codigo
            AND m.ano = {ano}
        """
    ).fetchone()[0]


    esperado_catalogo = con.execute(
        f"""
        SELECT COALESCE(
            SUM(observacoes_inmet),
            0
        )

        FROM matches

        WHERE ano = {ano}
        """
    ).fetchone()[0]


    print(
        f"\nINMET elegível no Parquet: "
        f"{inmet_elegiveis:,}"
    )


    print(
        f"Esperado pelo mapeamento: "
        f"{esperado_catalogo:,}"
    )


    if (
        inmet_elegiveis
        != esperado_catalogo
    ):

        raise RuntimeError(
            f"{ano}: número de observações "
            "INMET elegíveis não corresponde "
            "ao catálogo."
        )


    # ======================================================
    # 4.5 CONTAR OBSERVAÇÕES SEM ERA5
    # ======================================================

    sem_era5 = con.execute(
        f"""
        SELECT COUNT(*)

        FROM read_parquet(
            '{inmet_sql}'
        ) AS i

        INNER JOIN matches AS m

            ON i.codigo = m.codigo
            AND m.ano = {ano}

        LEFT JOIN read_parquet(
            '{era5_sql}'
        ) AS e

            ON e.datetime_utc
                = i.datetime_utc

            AND e.grid_index
                = m.grid_index

        WHERE e.datetime_utc IS NULL
        """
    ).fetchone()[0]


    # ======================================================
    # 4.6 ESCREVER PARES
    # ======================================================

    con.execute(
        f"""
        COPY (

            SELECT
                CAST(
                    {ano}
                    AS SMALLINT
                ) AS ano,

                CAST(
                    i.codigo
                    AS VARCHAR
                ) AS codigo,

                i.datetime_utc,

                CAST(
                    m.grid_index
                    AS INTEGER
                ) AS grid_index,

                CAST(
                    i.temp_max_hora_ant_c
                    AS REAL
                ) AS temp_inmet_c,

                CAST(
                    e.temp_era5_c
                    AS REAL
                ) AS temp_era5_c,

                CAST(
                    e.temp_era5_c
                    -
                    i.temp_max_hora_ant_c

                    AS REAL
                ) AS erro_c

            FROM read_parquet(
                '{inmet_sql}'
            ) AS i

            INNER JOIN matches AS m

                ON i.codigo = m.codigo
                AND m.ano = {ano}

            INNER JOIN read_parquet(
                '{era5_sql}'
            ) AS e

                ON e.datetime_utc
                    = i.datetime_utc

                AND e.grid_index
                    = m.grid_index

            ORDER BY
                i.codigo,
                i.datetime_utc
        )

        TO '{saida_sql}'

        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )


    # ======================================================
    # 4.7 VALIDAR PARQUET GERADO
    # ======================================================

    pares = con.execute(
        f"""
        SELECT COUNT(*)
        FROM read_parquet(
            '{saida_sql}'
        )
        """
    ).fetchone()[0]


    duplicados_saida = con.execute(
        f"""
        SELECT COUNT(*)

        FROM (
            SELECT
                codigo,
                datetime_utc,
                COUNT(*) AS n

            FROM read_parquet(
                '{saida_sql}'
            )

            GROUP BY
                codigo,
                datetime_utc

            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]


    nulos_saida = con.execute(
        f"""
        SELECT COUNT(*)

        FROM read_parquet(
            '{saida_sql}'
        )

        WHERE
            temp_inmet_c IS NULL
            OR
            temp_era5_c IS NULL
            OR
            erro_c IS NULL
        """
    ).fetchone()[0]


    # ======================================================
    # 4.8 SANIDADE DAS TEMPERATURAS
    # ======================================================

    estatisticas = con.execute(
        f"""
        SELECT
            MIN(temp_inmet_c),
            MAX(temp_inmet_c),

            MIN(temp_era5_c),
            MAX(temp_era5_c),

            MIN(erro_c),
            MAX(erro_c)

        FROM read_parquet(
            '{saida_sql}'
        )
        """
    ).fetchone()


    (
        min_inmet,
        max_inmet,
        min_era5,
        max_era5,
        min_erro,
        max_erro,
    ) = estatisticas


    # ======================================================
    # 4.9 STATUS
    # ======================================================

    match_pct = (
        pares
        /
        inmet_elegiveis
        *
        100
        if inmet_elegiveis > 0
        else 0.0
    )


    tamanho_mb = (
        saida_file.stat().st_size
        /
        1024**2
    )


    status = (
        "OK"
        if (
            pares
            ==
            inmet_elegiveis
            and
            sem_era5
            ==
            0
            and
            duplicados_saida
            ==
            0
            and
            nulos_saida
            ==
            0
        )
        else
        "ERRO"
    )


    if status != "OK":

        tudo_ok = False


    print(
        f"\nPares encontrados: "
        f"{pares:,}"
    )


    print(
        f"Sem ERA5 correspondente: "
        f"{sem_era5:,}"
    )


    print(
        f"Taxa de pareamento: "
        f"{match_pct:.4f}%"
    )


    print(
        f"Duplicados na saída: "
        f"{duplicados_saida:,}"
    )


    print(
        f"Nulos na saída: "
        f"{nulos_saida:,}"
    )


    print(
        "\nIntervalos:"
    )


    print(
        f"  INMET: "
        f"{min_inmet:.2f} a "
        f"{max_inmet:.2f} °C"
    )


    print(
        f"  ERA5:  "
        f"{min_era5:.2f} a "
        f"{max_era5:.2f} °C"
    )


    print(
        f"  Erro:  "
        f"{min_erro:+.2f} a "
        f"{max_erro:+.2f} °C"
    )


    print(
        f"\nArquivo: "
        f"{saida_file.name}"
    )


    print(
        f"Tamanho: "
        f"{tamanho_mb:.2f} MB"
    )


    print(
        f"STATUS: "
        f"{status}"
    )


    # ======================================================
    # 4.10 RESUMO
    # ======================================================

    resumo.append(
        {
            "ano":
                ano,

            "estacoes_elegiveis":
                estacoes_ano,

            "celulas_era5":
                celulas_ano,

            "inmet_elegiveis":
                inmet_elegiveis,

            "esperado_catalogo":
                esperado_catalogo,

            "pares_encontrados":
                pares,

            "sem_era5":
                sem_era5,

            "match_pct":
                match_pct,

            "duplicados_inmet":
                duplicados_inmet,

            "duplicados_era5":
                duplicados_era5,

            "duplicados_saida":
                duplicados_saida,

            "nulos_saida":
                nulos_saida,

            "temp_inmet_min_c":
                min_inmet,

            "temp_inmet_max_c":
                max_inmet,

            "temp_era5_min_c":
                min_era5,

            "temp_era5_max_c":
                max_era5,

            "erro_min_c":
                min_erro,

            "erro_max_c":
                max_erro,

            "arquivo_mb":
                tamanho_mb,

            "status":
                status,
        }
    )


# ==========================================================
# 5. SALVAR RESUMO
# ==========================================================

df_resumo = pd.DataFrame(
    resumo
)


df_resumo.to_csv(
    ARQUIVO_RESUMO,
    index=False,
    encoding="utf-8",
)


# ==========================================================
# 6. RESUMO GLOBAL
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO GLOBAL")
print("=" * 90)


total_inmet = int(
    df_resumo[
        "inmet_elegiveis"
    ].sum()
)


total_pares = int(
    df_resumo[
        "pares_encontrados"
    ].sum()
)


total_sem_era5 = int(
    df_resumo[
        "sem_era5"
    ].sum()
)


match_global = (
    total_pares
    /
    total_inmet
    *
    100
)


print(
    f"\nObservações INMET elegíveis: "
    f"{total_inmet:,}"
)


print(
    f"Pares ERA5 × INMET: "
    f"{total_pares:,}"
)


print(
    f"Sem ERA5 correspondente: "
    f"{total_sem_era5:,}"
)


print(
    f"Taxa global de pareamento: "
    f"{match_global:.6f}%"
)


print(
    f"\nAnos com erro: "
    f"{(df_resumo['status'] != 'OK').sum():,}"
)


print(
    f"Tamanho total dos pares: "
    f"{df_resumo['arquivo_mb'].sum():,.2f} MB"
)


print(
    "\nResumo salvo em:"
)

print(
    ARQUIVO_RESUMO
)


print(
    "\nParquets de pares:"
)

print(
    PARES_DIR
)


print("\n" + "=" * 90)


if tudo_ok:

    print(
        "RESULTADO: PAREAMENTO TEMPORAL APROVADO"
    )

else:

    print(
        "RESULTADO: PAREAMENTO TEMPORAL "
        "REQUER INVESTIGAÇÃO"
    )


print("=" * 90)


con.close()