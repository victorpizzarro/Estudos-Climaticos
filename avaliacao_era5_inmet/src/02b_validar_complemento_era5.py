from datetime import datetime

import numpy as np

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_get_values,
    codes_release,
)

from config import ERA5_COMPLEMENTO_TESTE


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

HORARIOS_ESPERADOS = {
    datetime(2020, 10, 3, 0, 0),
    datetime(2020, 10, 3, 1, 0),
    datetime(2020, 10, 3, 2, 0),
    datetime(2020, 10, 3, 3, 0),
    datetime(2020, 10, 3, 22, 0),
    datetime(2020, 10, 3, 23, 0),
}


# ==========================================================
# FUNÇÃO AUXILIAR
# ==========================================================

def obter(gid, chave):

    try:
        return codes_get(gid, chave)

    except Exception:
        return None


def montar_datetime(data_grib, hora_grib):

    data_grib = int(data_grib)
    hora_grib = int(hora_grib)

    ano = data_grib // 10000
    mes = (data_grib // 100) % 100
    dia = data_grib % 100

    hora = hora_grib // 100
    minuto = hora_grib % 100

    return datetime(
        ano,
        mes,
        dia,
        hora,
        minuto,
    )


# ==========================================================
# INÍCIO
# ==========================================================

print("=" * 90)
print("VALIDAÇÃO DO COMPLEMENTO ERA5")
print("=" * 90)

print("\nArquivo:")
print(ERA5_COMPLEMENTO_TESTE)


if not ERA5_COMPLEMENTO_TESTE.exists():

    raise FileNotFoundError(
        f"\nArquivo não encontrado:\n"
        f"{ERA5_COMPLEMENTO_TESTE}"
    )


print(
    f"\nTamanho: "
    f"{ERA5_COMPLEMENTO_TESTE.stat().st_size:,} bytes"
)


# ==========================================================
# CONTADORES
# ==========================================================

contador = 0

valid_times = []

variaveis = set()

steps = set()

step_ranges = set()

tipos_step = set()

grades = set()

problemas = []


# ==========================================================
# LEITURA DO GRIB
# ==========================================================

with open(
    ERA5_COMPLEMENTO_TESTE,
    "rb",
) as arquivo:

    while True:

        gid = codes_grib_new_from_file(
            arquivo
        )

        if gid is None:
            break

        contador += 1

        try:

            print("\n" + "-" * 90)
            print(f"MENSAGEM {contador}")
            print("-" * 90)

            edition = obter(
                gid,
                "edition",
            )

            short_name = obter(
                gid,
                "shortName",
            )

            param_id = obter(
                gid,
                "paramId",
            )

            data_type = obter(
                gid,
                "dataType",
            )

            step_type = obter(
                gid,
                "stepType",
            )

            start_step = obter(
                gid,
                "startStep",
            )

            end_step = obter(
                gid,
                "endStep",
            )

            step_range = obter(
                gid,
                "stepRange",
            )

            data_date = obter(
                gid,
                "dataDate",
            )

            data_time = obter(
                gid,
                "dataTime",
            )

            validity_date = obter(
                gid,
                "validityDate",
            )

            validity_time = obter(
                gid,
                "validityTime",
            )

            nx = obter(
                gid,
                "Nx",
            )

            ny = obter(
                gid,
                "Ny",
            )

            lat_first = obter(
                gid,
                "latitudeOfFirstGridPointInDegrees",
            )

            lat_last = obter(
                gid,
                "latitudeOfLastGridPointInDegrees",
            )

            lon_first = obter(
                gid,
                "longitudeOfFirstGridPointInDegrees",
            )

            lon_last = obter(
                gid,
                "longitudeOfLastGridPointInDegrees",
            )

            grid_type = obter(
                gid,
                "gridType",
            )

            unidades = obter(
                gid,
                "units",
            )


            # ==============================================
            # VALID TIME REAL
            # ==============================================

            valid_datetime = montar_datetime(
                validity_date,
                validity_time,
            )

            valid_times.append(
                valid_datetime
            )


            # ==============================================
            # VALORES
            # ==============================================

            valores = np.asarray(
                codes_get_values(gid),
                dtype=float,
            )

            quantidade_nan = int(
                np.isnan(valores).sum()
            )

            valor_min = float(
                np.nanmin(valores)
            )

            valor_max = float(
                np.nanmax(valores)
            )


            # ==============================================
            # COLETAR INFORMAÇÕES
            # ==============================================

            variaveis.add(
                short_name
            )

            steps.add(
                (start_step, end_step)
            )

            step_ranges.add(
                str(step_range)
            )

            tipos_step.add(
                step_type
            )

            grades.add(
                (
                    nx,
                    ny,
                    lat_first,
                    lat_last,
                    lon_first,
                    lon_last,
                    grid_type,
                )
            )


            # ==============================================
            # EXIBIÇÃO
            # ==============================================

            print(
                f"GRIB edition:   {edition}"
            )

            print(
                f"shortName:      {short_name}"
            )

            print(
                f"paramId:        {param_id}"
            )

            print(
                f"dataType:       {data_type}"
            )

            print(
                f"stepType:       {step_type}"
            )

            print(
                f"startStep:      {start_step}"
            )

            print(
                f"endStep:        {end_step}"
            )

            print(
                f"stepRange:      {step_range}"
            )

            print(
                f"dataDate:       {data_date}"
            )

            print(
                f"dataTime:       {data_time}"
            )

            print(
                f"validityDate:   {validity_date}"
            )

            print(
                f"validityTime:   {validity_time}"
            )

            print(
                f"VALID TIME:     {valid_datetime}"
            )

            print(
                f"unidades:       {unidades}"
            )

            print(
                f"gridType:       {grid_type}"
            )

            print(
                f"Nx × Ny:        {nx} × {ny}"
            )

            print(
                f"latitude:       "
                f"{lat_first} → {lat_last}"
            )

            print(
                f"longitude:      "
                f"{lon_first} → {lon_last}"
            )

            print(
                f"pontos:         "
                f"{len(valores):,}"
            )

            print(
                f"NaN:            "
                f"{quantidade_nan:,}"
            )

            print(
                f"mínimo:         "
                f"{valor_min:.4f} K"
            )

            print(
                f"máximo:         "
                f"{valor_max:.4f} K"
            )

            print(
                f"máximo °C:      "
                f"{valor_max - 273.15:.4f} °C"
            )


            # ==============================================
            # TESTES INDIVIDUAIS
            # ==============================================

            if short_name != "mx2t":

                problemas.append(
                    f"Mensagem {contador}: "
                    f"variável inesperada "
                    f"{short_name}"
                )


            if step_type != "max":

                problemas.append(
                    f"Mensagem {contador}: "
                    f"stepType inesperado "
                    f"{step_type}"
                )


            if nx != 161 or ny != 161:

                problemas.append(
                    f"Mensagem {contador}: "
                    f"grade inesperada "
                    f"{nx} × {ny}"
                )


            if quantidade_nan > 0:

                problemas.append(
                    f"Mensagem {contador}: "
                    f"{quantidade_nan} NaN"
                )


        finally:

            codes_release(
                gid
            )


# ==========================================================
# RESUMO
# ==========================================================

print("\n" + "=" * 90)
print("RESUMO")
print("=" * 90)


print(
    f"\nQuantidade de mensagens: "
    f"{contador}"
)


print(
    "\nVariáveis encontradas:"
)

for item in sorted(
    str(x)
    for x in variaveis
):

    print(
        f"  {item}"
    )


print(
    "\nStep ranges encontrados:"
)

for item in sorted(
    step_ranges
):

    print(
        f"  {item}"
    )


print(
    "\nValid times encontrados:"
)

for horario in sorted(
    valid_times
):

    print(
        f"  {horario}"
    )


# ==========================================================
# COMPARAR HORÁRIOS
# ==========================================================

horarios_encontrados = set(
    valid_times
)


faltantes = (
    HORARIOS_ESPERADOS
    -
    horarios_encontrados
)


extras = (
    horarios_encontrados
    -
    HORARIOS_ESPERADOS
)


print("\n" + "=" * 90)
print("VERIFICAÇÕES")
print("=" * 90)


print(
    "\nQuantidade esperada de mensagens: 6"
)

print(
    f"Quantidade encontrada: {contador}"
)

print(
    "Quantidade correta:",
    contador == 6,
)


print(
    "\nTodos os horários esperados encontrados:",
    len(faltantes) == 0,
)


if faltantes:

    print("\nHorários faltantes:")

    for horario in sorted(
        faltantes
    ):

        print(
            " ",
            horario,
        )


print(
    "\nHorários inesperados encontrados:",
    len(extras) > 0,
)


if extras:

    for horario in sorted(
        extras
    ):

        print(
            " ",
            horario,
        )


print(
    "\nÚnica variável é mx2t:",
    variaveis == {"mx2t"},
)


print(
    "\nÚnico stepType é max:",
    tipos_step == {"max"},
)


print(
    "\nQuantidade de grades diferentes:",
    len(grades),
)


# ==========================================================
# PROBLEMAS
# ==========================================================

print("\n" + "=" * 90)
print("PROBLEMAS DETECTADOS")
print("=" * 90)


if not problemas:

    print(
        "\nNenhum problema detectado."
    )

else:

    for problema in problemas:

        print(
            f"\n- {problema}"
        )


# ==========================================================
# RESULTADO FINAL
# ==========================================================

aprovado = (
    contador == 6
    and len(faltantes) == 0
    and len(extras) == 0
    and variaveis == {"mx2t"}
    and tipos_step == {"max"}
    and len(grades) == 1
    and len(problemas) == 0
)


print("\n" + "=" * 90)

if aprovado:

    print(
        "RESULTADO: COMPLEMENTO APROVADO"
    )

else:

    print(
        "RESULTADO: COMPLEMENTO REQUER REVISÃO"
    )

print("=" * 90)