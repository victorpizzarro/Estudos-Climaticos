from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)

from config import ERA5_GRIB


# ==========================================================
# FUNÇÃO SEGURA PARA LER CHAVES GRIB
# ==========================================================

def obter_chave(gid, chave):
    """
    Tenta ler uma chave do GRIB.

    Algumas chaves podem não existir dependendo
    da edição ou configuração do arquivo.
    """

    try:
        return codes_get(gid, chave)

    except Exception:
        return "N/D"


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 100)

print(
    "INSPEÇÃO DOS INTERVALOS TEMPORAIS "
    "DA VARIÁVEL mx2t"
)

print("=" * 100)

print("\nArquivo:")
print(ERA5_GRIB)


# ==========================================================
# ABERTURA DO GRIB
# ==========================================================

contador_mx2t = 0

limite = 24


with open(ERA5_GRIB, "rb") as arquivo:

    while True:

        gid = codes_grib_new_from_file(
            arquivo
        )

        if gid is None:
            break


        short_name = obter_chave(
            gid,
            "shortName"
        )


        # --------------------------------------------------
        # SOMENTE mx2t
        # --------------------------------------------------

        if short_name == "mx2t":

            contador_mx2t += 1


            data = obter_chave(
                gid,
                "dataDate"
            )

            hora = obter_chave(
                gid,
                "dataTime"
            )


            start_step = obter_chave(
                gid,
                "startStep"
            )

            end_step = obter_chave(
                gid,
                "endStep"
            )

            step_range = obter_chave(
                gid,
                "stepRange"
            )

            step_type = obter_chave(
                gid,
                "stepType"
            )


            validity_date = obter_chave(
                gid,
                "validityDate"
            )

            validity_time = obter_chave(
                gid,
                "validityTime"
            )


            print("\n" + "-" * 100)

            print(
                f"MENSAGEM mx2t "
                f"{contador_mx2t}"
            )

            print("-" * 100)


            print(
                f"dataDate:      {data}"
            )

            print(
                f"dataTime:      {hora}"
            )

            print(
                f"startStep:     {start_step}"
            )

            print(
                f"endStep:       {end_step}"
            )

            print(
                f"stepRange:     {step_range}"
            )

            print(
                f"stepType:      {step_type}"
            )

            print(
                f"validityDate:  {validity_date}"
            )

            print(
                f"validityTime:  {validity_time}"
            )


        codes_release(
            gid
        )


        # --------------------------------------------------
        # NÃO PRECISAMOS LER O ARQUIVO INTEIRO
        # --------------------------------------------------

        if contador_mx2t >= limite:
            break


# ==========================================================
# FINAL
# ==========================================================

print("\n" + "=" * 100)

print(
    f"{contador_mx2t} mensagens "
    f"mx2t foram examinadas."
)

print("=" * 100)