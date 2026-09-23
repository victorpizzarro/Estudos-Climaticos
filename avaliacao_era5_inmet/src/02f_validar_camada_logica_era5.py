from datetime import datetime, timedelta
from collections import Counter

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)

from config import (
    ERA5_GRIB,
    ERA5_COMPLEMENTO_ANOS_DIR,
    TABLES_DIR,
)


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

ANO_INICIAL = 1995
ANO_FINAL = 2025

INICIO = datetime(
    1995,
    1,
    1,
    0,
    0,
)

FIM = datetime(
    2026,
    1,
    1,
    0,
    0,
)


TABLES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==========================================================
# FUNÇÃO PARA MONTAR DATETIME DO GRIB
# ==========================================================

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
# FUNÇÃO PARA LER VALID TIMES DE UM GRIB
# ==========================================================

def ler_valid_times(
    caminho,
    origem,
):

    print("\n" + "=" * 90)

    print(
        f"LENDO: {origem}"
    )

    print("=" * 90)

    print(
        caminho
    )


    horarios = []

    contador = 0

    problemas = []


    with open(
        caminho,
        "rb",
    ) as arquivo:

        while True:

            gid = (
                codes_grib_new_from_file(
                    arquivo
                )
            )


            if gid is None:
                break


            try:

                short_name = codes_get(
                    gid,
                    "shortName",
                )


                if short_name != "mx2t":
                    continue


                contador += 1


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


                data_hora = montar_datetime(
                    validity_date,
                    validity_time,
                )


                # ------------------------------------------
                # Considerar somente 1995–2025
                # ------------------------------------------

                if (
                    data_hora >= INICIO
                    and data_hora < FIM
                ):

                    horarios.append(
                        data_hora
                    )


                # ------------------------------------------
                # Progresso
                # ------------------------------------------

                if contador % 50000 == 0:

                    print(
                        f"{contador:,} mensagens "
                        "mx2t examinadas..."
                    )


            except Exception as erro:

                problemas.append(
                    str(erro)
                )


            finally:

                codes_release(
                    gid
                )


    print(
        f"\nMensagens mx2t examinadas: "
        f"{contador:,}"
    )

    print(
        f"Horários dentro de "
        f"1995–2025: "
        f"{len(horarios):,}"
    )


    if problemas:

        print(
            f"Problemas encontrados: "
            f"{len(problemas)}"
        )

    else:

        print(
            "Problemas encontrados: 0"
        )


    return horarios


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)

print(
    "VALIDAÇÃO DA CAMADA LÓGICA ERA5 COMPLETA"
)

print("=" * 90)

print(
    "\nObjetivo:"
)

print(
    "GRIB original + complementos = "
    "todas as horas de 1995–2025"
)


# ==========================================================
# 1. LER ORIGINAL
# ==========================================================

horarios_original = (
    ler_valid_times(
        ERA5_GRIB,
        "GRIB ORIGINAL",
    )
)


# ==========================================================
# 2. LER COMPLEMENTOS
# ==========================================================

horarios_complemento = []


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    arquivo = (
        ERA5_COMPLEMENTO_ANOS_DIR
        / f"mx2t_faltantes_{ano}.grib"
    )


    if not arquivo.exists():

        raise FileNotFoundError(
            f"Complemento ausente: {arquivo}"
        )


    horarios_ano = ler_valid_times(
        arquivo,
        f"COMPLEMENTO {ano}",
    )


    horarios_complemento.extend(
        horarios_ano
    )


# ==========================================================
# 3. CONTAGEM DAS FONTES
# ==========================================================

print("\n" + "=" * 90)

print(
    "CONTAGEM DAS FONTES"
)

print("=" * 90)


print(
    f"\nOriginal: "
    f"{len(horarios_original):,}"
)


print(
    f"Complementos: "
    f"{len(horarios_complemento):,}"
)


print(
    f"Soma: "
    f"{len(horarios_original) + len(horarios_complemento):,}"
)


# ==========================================================
# 4. VERIFICAR DUPLICADOS INTERNOS
# ==========================================================

original_set = set(
    horarios_original
)

complemento_set = set(
    horarios_complemento
)


duplicados_original = (
    len(horarios_original)
    -
    len(original_set)
)


duplicados_complemento = (
    len(horarios_complemento)
    -
    len(complemento_set)
)


print(
    f"\nDuplicados no original: "
    f"{duplicados_original:,}"
)


print(
    f"Duplicados nos complementos: "
    f"{duplicados_complemento:,}"
)


# ==========================================================
# 5. VERIFICAR SOBREPOSIÇÃO ENTRE FONTES
# ==========================================================

sobreposicao = (
    original_set
    &
    complemento_set
)


print(
    f"\nHorários presentes "
    f"nas DUAS fontes: "
    f"{len(sobreposicao):,}"
)


if sobreposicao:

    print(
        "\nPrimeiras sobreposições:"
    )

    for horario in sorted(
        sobreposicao
    )[:20]:

        print(
            " ",
            horario,
        )


# ==========================================================
# 6. CAMADA LÓGICA
# ==========================================================

camada_logica = (
    original_set
    |
    complemento_set
)


print("\n" + "=" * 90)

print(
    "CAMADA LÓGICA"
)

print("=" * 90)


print(
    f"\nHorários únicos combinados: "
    f"{len(camada_logica):,}"
)


# ==========================================================
# 7. GERAR TODAS AS HORAS ESPERADAS
# ==========================================================

esperados = set()


atual = INICIO


while atual < FIM:

    esperados.add(
        atual
    )

    atual += timedelta(
        hours=1
    )


print(
    f"Horários esperados: "
    f"{len(esperados):,}"
)


# ==========================================================
# 8. FALTANTES E EXTRAS
# ==========================================================

faltantes = (
    esperados
    -
    camada_logica
)


extras = (
    camada_logica
    -
    esperados
)


print(
    f"\nHorários faltantes: "
    f"{len(faltantes):,}"
)


print(
    f"Horários extras: "
    f"{len(extras):,}"
)


if faltantes:

    print(
        "\nPrimeiros horários faltantes:"
    )

    for horario in sorted(
        faltantes
    )[:20]:

        print(
            " ",
            horario,
        )


if extras:

    print(
        "\nPrimeiros horários extras:"
    )

    for horario in sorted(
        extras
    )[:20]:

        print(
            " ",
            horario,
        )


# ==========================================================
# 9. COBERTURA POR HORA UTC
# ==========================================================

print("\n" + "=" * 90)

print(
    "COBERTURA POR HORA UTC"
)

print("=" * 90)


contador_horas = Counter(
    horario.hour
    for horario in camada_logica
)


dias_totais = (
    len(esperados)
    // 24
)


for hora in range(24):

    quantidade = (
        contador_horas[
            hora
        ]
    )


    cobertura = (
        quantidade
        /
        dias_totais
        *
        100
    )


    print(
        f"{hora:02d}:00 UTC | "
        f"{quantidade:>6,} | "
        f"{cobertura:6.2f}%"
    )


# ==========================================================
# 10. COBERTURA POR ANO
# ==========================================================

print("\n" + "=" * 90)

print(
    "COBERTURA POR ANO"
)

print("=" * 90)


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    encontrados_ano = sum(
        1
        for horario
        in camada_logica
        if horario.year == ano
    )


    inicio_ano = datetime(
        ano,
        1,
        1,
    )


    fim_ano = datetime(
        ano + 1,
        1,
        1,
    )


    esperado_ano = int(
        (
            fim_ano
            -
            inicio_ano
        ).total_seconds()
        / 3600
    )


    cobertura = (
        encontrados_ano
        /
        esperado_ano
        *
        100
    )


    print(
        f"{ano}: "
        f"{encontrados_ano:,} / "
        f"{esperado_ano:,} "
        f"({cobertura:.2f}%)"
    )


# ==========================================================
# 11. VERIFICAÇÃO FINAL
# ==========================================================

TOTAL_ESPERADO = 271752

TOTAL_ORIGINAL_ESPERADO = 203814

TOTAL_COMPLEMENTO_ESPERADO = 67938


aprovado = (

    len(original_set)
    == TOTAL_ORIGINAL_ESPERADO

    and

    len(complemento_set)
    == TOTAL_COMPLEMENTO_ESPERADO

    and

    len(camada_logica)
    == TOTAL_ESPERADO

    and

    len(sobreposicao)
    == 0

    and

    len(faltantes)
    == 0

    and

    len(extras)
    == 0

    and

    duplicados_original
    == 0

    and

    duplicados_complemento
    == 0
)


# ==========================================================
# RESULTADO
# ==========================================================

print("\n" + "=" * 90)


if aprovado:

    print(
        "RESULTADO: CAMADA LÓGICA ERA5 APROVADA"
    )

    print()

    print(
        "Original:     "
        "203.814 horas"
    )

    print(
        "Complemento:   "
        "67.938 horas"
    )

    print(
        "Total:        "
        "271.752 horas"
    )

    print()

    print(
        "Cobertura temporal: 100%"
    )

    print(
        "Período: "
        "01/01/1995 00 UTC "
        "até "
        "31/12/2025 23 UTC"
    )

else:

    print(
        "RESULTADO: CAMADA LÓGICA "
        "REQUER INVESTIGAÇÃO"
    )


print("=" * 90)