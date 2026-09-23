from collections import Counter

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)

from config import ERA5_GRIB


print("=" * 80)
print("VALIDAÇÃO COMPLETA DOS INTERVALOS mx2t")
print("=" * 80)

print("\nArquivo:")
print(ERA5_GRIB)


# ==========================================================
# CONTADORES
# ==========================================================

total_mx2t = 0

intervalos = Counter()

pares_steps = Counter()

horas_base = Counter()

anomalias = []


# ==========================================================
# LEITURA SEQUENCIAL DOS CABEÇALHOS
# ==========================================================

with open(ERA5_GRIB, "rb") as arquivo:

    while True:

        gid = codes_grib_new_from_file(arquivo)

        if gid is None:
            break

        try:

            short_name = codes_get(
                gid,
                "shortName",
            )

            if short_name != "mx2t":
                continue


            total_mx2t += 1


            start_step = int(
                codes_get(
                    gid,
                    "startStep",
                )
            )

            end_step = int(
                codes_get(
                    gid,
                    "endStep",
                )
            )

            step_range = str(
                codes_get(
                    gid,
                    "stepRange",
                )
            )

            data_time = int(
                codes_get(
                    gid,
                    "dataTime",
                )
            )


            intervalos[
                step_range
            ] += 1


            pares_steps[
                (
                    start_step,
                    end_step,
                )
            ] += 1


            horas_base[
                data_time
            ] += 1


            # Intervalo deve ter exatamente 1 hora
            if end_step - start_step != 1:

                anomalias.append(
                    (
                        total_mx2t,
                        start_step,
                        end_step,
                        step_range,
                    )
                )


            if total_mx2t % 25000 == 0:

                print(
                    f"{total_mx2t:,} "
                    "mensagens mx2t analisadas..."
                )


        finally:

            codes_release(gid)


# ==========================================================
# RESULTADOS
# ==========================================================

print("\n" + "=" * 80)
print("RESULTADOS")
print("=" * 80)


print(
    f"\nTotal de mensagens mx2t: "
    f"{total_mx2t:,}"
)


print("\nIntervalos encontrados:")

for intervalo, quantidade in sorted(
    intervalos.items()
):

    print(
        f"{intervalo:>8}: "
        f"{quantidade:,}"
    )


print("\nPares startStep → endStep:")

for par, quantidade in sorted(
    pares_steps.items()
):

    inicio, fim = par

    print(
        f"{inicio:2d} → {fim:2d}: "
        f"{quantidade:,}"
    )


print("\nHorários de inicialização:")

for hora, quantidade in sorted(
    horas_base.items()
):

    print(
        f"{hora:04d} UTC: "
        f"{quantidade:,}"
    )


# ==========================================================
# INTERVALOS ESPERADOS
# ==========================================================

esperados = {
    f"{i}-{i + 1}"
    for i in range(12)
}


encontrados = set(
    intervalos.keys()
)


faltantes = (
    esperados
    -
    encontrados
)


extras = (
    encontrados
    -
    esperados
)


print("\n" + "=" * 80)
print("VERIFICAÇÕES")
print("=" * 80)


print(
    "\nTodos os 12 intervalos "
    "horários encontrados:",
    faltantes == set(),
)


if faltantes:

    print(
        "Intervalos faltantes:",
        sorted(faltantes),
    )


print(
    "\nExistem intervalos inesperados:",
    len(extras) > 0,
)


if extras:

    print(
        "Intervalos extras:",
        sorted(extras),
    )


print(
    "\nMensagens com intervalo "
    "diferente de 1 hora:",
    len(anomalias),
)


if anomalias:

    print("\nPrimeiras anomalias:")

    for item in anomalias[:10]:

        print(item)


# ==========================================================
# EXPECTATIVA A PARTIR DO XARRAY
# ==========================================================

TIME_COUNT = 22647
STEP_COUNT = 12

esperado_total = (
    TIME_COUNT
    *
    STEP_COUNT
)


print(
    f"\nTotal esperado pela estrutura "
    f"time × step:"
)

print(
    f"{TIME_COUNT:,} × "
    f"{STEP_COUNT} = "
    f"{esperado_total:,}"
)


print(
    "\nTotal GRIB igual ao esperado:",
    total_mx2t == esperado_total,
)


print("\n" + "=" * 80)
print("VALIDAÇÃO FINALIZADA")
print("=" * 80)