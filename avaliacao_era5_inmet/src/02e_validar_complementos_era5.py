from calendar import isleap
from datetime import datetime, timedelta
import csv

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)

from config import (
    ERA5_COMPLEMENTO_ANOS_DIR,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ANO_INICIAL = 1995
ANO_FINAL = 2025

HORAS_ESPERADAS = {
    0,
    100,
    200,
    300,
    2200,
    2300,
}


# ==========================================================
# DIRETÓRIO DE SAÍDA
# ==========================================================

TABLES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

arquivo_csv = (
    TABLES_DIR
    / "validacao_complementos_era5.csv"
)


# ==========================================================
# FUNÇÕES
# ==========================================================

def mensagens_esperadas(ano):

    dias = (
        366
        if isleap(ano)
        else 365
    )

    return dias * 6


def gerar_datas_esperadas(ano):
    """
    Gera exatamente os horários:
    00, 01, 02, 03, 22 e 23 UTC
    de todos os dias do ano.
    """

    inicio = datetime(
        ano,
        1,
        1,
    )

    fim = datetime(
        ano + 1,
        1,
        1,
    )

    horarios = set()

    atual = inicio

    while atual < fim:

        for hora in [
            0,
            1,
            2,
            3,
            22,
            23,
        ]:

            horarios.add(
                atual.replace(
                    hour=hora
                )
            )

        atual += timedelta(
            days=1
        )

    return horarios


def montar_datetime(
    validity_date,
    validity_time,
):

    validity_date = int(
        validity_date
    )

    validity_time = int(
        validity_time
    )

    ano = (
        validity_date
        // 10000
    )

    mes = (
        validity_date
        // 100
    ) % 100

    dia = (
        validity_date
        % 100
    )

    hora = (
        validity_time
        // 100
    )

    minuto = (
        validity_time
        % 100
    )

    return datetime(
        ano,
        mes,
        dia,
        hora,
        minuto,
    )


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)

print(
    "VALIDAÇÃO GLOBAL DOS COMPLEMENTOS ERA5"
)

print("=" * 90)

print(
    f"\nPeríodo: "
    f"{ANO_INICIAL}-{ANO_FINAL}"
)

print(
    "\nDiretório:"
)

print(
    ERA5_COMPLEMENTO_ANOS_DIR
)


# ==========================================================
# VERIFICAR ARQUIVOS .PART
# ==========================================================

arquivos_part = list(
    ERA5_COMPLEMENTO_ANOS_DIR.glob(
        "*.part"
    )
)


print(
    f"\nArquivos .part encontrados: "
    f"{len(arquivos_part)}"
)


if arquivos_part:

    print(
        "\nATENÇÃO: existem arquivos parciais:"
    )

    for arquivo in arquivos_part:

        print(
            " ",
            arquivo.name,
        )


# ==========================================================
# CONTADORES GERAIS
# ==========================================================

total_esperado = 0
total_encontrado = 0

anos_aprovados = []
anos_reprovados = []

resumo_csv = []

todos_valid_times = set()

duplicados_globais = 0


# ==========================================================
# LOOP POR ANO
# ==========================================================

for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    print("\n" + "=" * 90)
    print(f"ANO {ano}")
    print("=" * 90)


    arquivo = (
        ERA5_COMPLEMENTO_ANOS_DIR
        / f"mx2t_faltantes_{ano}.grib"
    )


    esperado = mensagens_esperadas(
        ano
    )


    total_esperado += esperado


    # ======================================================
    # ARQUIVO EXISTE?
    # ======================================================

    if not arquivo.exists():

        print(
            "\nARQUIVO AUSENTE:"
        )

        print(
            arquivo
        )

        anos_reprovados.append(
            ano
        )

        resumo_csv.append(
            {
                "ano": ano,
                "esperado": esperado,
                "encontrado": 0,
                "duplicados": 0,
                "faltantes": esperado,
                "extras": 0,
                "status": "REPROVADO",
            }
        )

        continue


    print(
        f"\nArquivo: "
        f"{arquivo.name}"
    )


    print(
        f"Tamanho: "
        f"{arquivo.stat().st_size / 1024**2:.2f} MB"
    )


    # ======================================================
    # VARIÁVEIS DE VALIDAÇÃO
    # ======================================================

    contador = 0

    valid_times = []

    horas = set()

    problemas = []


    # ======================================================
    # LEITURA
    # ======================================================

    with open(
        arquivo,
        "rb",
    ) as f:

        while True:

            gid = (
                codes_grib_new_from_file(
                    f
                )
            )

            if gid is None:
                break


            contador += 1


            try:

                short_name = (
                    codes_get(
                        gid,
                        "shortName",
                    )
                )


                param_id = int(
                    codes_get(
                        gid,
                        "paramId",
                    )
                )


                step_type = (
                    codes_get(
                        gid,
                        "stepType",
                    )
                )


                grid_type = (
                    codes_get(
                        gid,
                        "gridType",
                    )
                )


                nx = int(
                    codes_get(
                        gid,
                        "Nx",
                    )
                )


                ny = int(
                    codes_get(
                        gid,
                        "Ny",
                    )
                )


                validity_date = int(
                    codes_get(
                        gid,
                        "validityDate",
                    )
                )


                validity_time = int(
                    codes_get(
                        gid,
                        "validityTime",
                    )
                )


                # ==========================================
                # VALID TIME
                # ==========================================

                data_hora = montar_datetime(
                    validity_date,
                    validity_time,
                )


                valid_times.append(
                    data_hora
                )


                horas.add(
                    validity_time
                )


                # ==========================================
                # TESTES ESTRUTURAIS
                # ==========================================

                if short_name != "mx2t":

                    problemas.append(
                        f"shortName={short_name}"
                    )


                if param_id != 201:

                    problemas.append(
                        f"paramId={param_id}"
                    )


                if step_type != "max":

                    problemas.append(
                        f"stepType={step_type}"
                    )


                if grid_type != "regular_ll":

                    problemas.append(
                        f"gridType={grid_type}"
                    )


                if (
                    nx != 161
                    or ny != 161
                ):

                    problemas.append(
                        f"grade={nx}x{ny}"
                    )


                if (
                    data_hora.year
                    != ano
                ):

                    problemas.append(
                        f"ano incorreto: "
                        f"{data_hora}"
                    )


            finally:

                codes_release(
                    gid
                )


    # ======================================================
    # COMPARAÇÃO TEMPORAL
    # ======================================================

    encontrados_set = set(
        valid_times
    )


    esperado_set = (
        gerar_datas_esperadas(
            ano
        )
    )


    duplicados = (
        len(valid_times)
        -
        len(encontrados_set)
    )


    faltantes = (
        esperado_set
        -
        encontrados_set
    )


    extras = (
        encontrados_set
        -
        esperado_set
    )


    # ======================================================
    # DUPLICADOS ENTRE ANOS
    # ======================================================

    intersecao = (
        todos_valid_times
        &
        encontrados_set
    )


    duplicados_globais += len(
        intersecao
    )


    todos_valid_times.update(
        encontrados_set
    )


    total_encontrado += contador


    # ======================================================
    # STATUS
    # ======================================================

    aprovado = (
        contador == esperado
        and duplicados == 0
        and len(faltantes) == 0
        and len(extras) == 0
        and horas == HORAS_ESPERADAS
        and len(problemas) == 0
    )


    print(
        f"\nMensagens esperadas: "
        f"{esperado:,}"
    )


    print(
        f"Mensagens encontradas: "
        f"{contador:,}"
    )


    print(
        f"Datas únicas: "
        f"{len(encontrados_set):,}"
    )


    print(
        f"Duplicados: "
        f"{duplicados:,}"
    )


    print(
        f"Horários: "
        f"{sorted(horas)}"
    )


    print(
        f"Faltantes: "
        f"{len(faltantes):,}"
    )


    print(
        f"Extras: "
        f"{len(extras):,}"
    )


    if aprovado:

        print(
            "\nSTATUS: APROVADO"
        )

        anos_aprovados.append(
            ano
        )

        status = "APROVADO"

    else:

        print(
            "\nSTATUS: REPROVADO"
        )

        anos_reprovados.append(
            ano
        )

        status = "REPROVADO"


        if problemas:

            print(
                "\nPrimeiros problemas estruturais:"
            )

            for problema in problemas[:10]:

                print(
                    " ",
                    problema,
                )


        if faltantes:

            print(
                "\nPrimeiros horários faltantes:"
            )

            for data in sorted(
                faltantes
            )[:10]:

                print(
                    " ",
                    data,
                )


        if extras:

            print(
                "\nPrimeiros horários extras:"
            )

            for data in sorted(
                extras
            )[:10]:

                print(
                    " ",
                    data,
                )


    resumo_csv.append(
        {
            "ano": ano,
            "esperado": esperado,
            "encontrado": contador,
            "duplicados": duplicados,
            "faltantes": len(
                faltantes
            ),
            "extras": len(
                extras
            ),
            "status": status,
        }
    )


# ==========================================================
# SALVAR RESUMO CSV
# ==========================================================

with open(
    arquivo_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "ano",
            "esperado",
            "encontrado",
            "duplicados",
            "faltantes",
            "extras",
            "status",
        ],
    )

    writer.writeheader()

    writer.writerows(
        resumo_csv
    )


# ==========================================================
# RESUMO GLOBAL
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO GLOBAL")
print("=" * 90)


print(
    f"\nAnos esperados: "
    f"{ANO_FINAL - ANO_INICIAL + 1}"
)


print(
    f"Anos aprovados: "
    f"{len(anos_aprovados)}"
)


print(
    f"Anos reprovados: "
    f"{len(anos_reprovados)}"
)


print(
    f"\nMensagens esperadas: "
    f"{total_esperado:,}"
)


print(
    f"Mensagens encontradas: "
    f"{total_encontrado:,}"
)


print(
    f"Horários únicos totais: "
    f"{len(todos_valid_times):,}"
)


print(
    f"Duplicados entre anos: "
    f"{duplicados_globais:,}"
)


print(
    f"\nArquivos .part: "
    f"{len(arquivos_part)}"
)


print(
    "\nTabela de validação:"
)

print(
    arquivo_csv
)


# ==========================================================
# RESULTADO FINAL
# ==========================================================

aprovado_global = (
    len(anos_aprovados) == 31
    and len(anos_reprovados) == 0
    and total_esperado == 67938
    and total_encontrado == 67938
    and len(todos_valid_times) == 67938
    and duplicados_globais == 0
    and len(arquivos_part) == 0
)


print("\n" + "=" * 90)


if aprovado_global:

    print(
        "RESULTADO GLOBAL: COMPLEMENTOS APROVADOS"
    )

    print(
        "\n67.938 horários complementares "
        "foram validados."
    )

else:

    print(
        "RESULTADO GLOBAL: REQUER INVESTIGAÇÃO"
    )


print("=" * 90)