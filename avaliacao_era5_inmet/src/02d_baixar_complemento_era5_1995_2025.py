from calendar import isleap
from pathlib import Path
import time

import cdsapi

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)

from config import ERA5_COMPLEMENTO_ANOS_DIR


# ==========================================================
# CONFIGURAÇÕES GERAIS
# ==========================================================

ANO_INICIAL = 1995
ANO_FINAL = 2025

DATASET = "reanalysis-era5-single-levels"


# Horários que faltam no GRIB original
HORAS_FALTANTES = [
    "00:00",
    "01:00",
    "02:00",
    "03:00",
    "22:00",
    "23:00",
]


# Horas esperadas no campo validityTime do GRIB
HORAS_VALIDAS_ESPERADAS = {
    0,
    100,
    200,
    300,
    2200,
    2300,
}


MESES = [
    f"{mes:02d}"
    for mes in range(1, 13)
]


DIAS = [
    f"{dia:02d}"
    for dia in range(1, 32)
]


# Número máximo de tentativas por ano
MAX_TENTATIVAS = 5


# Espera progressiva entre tentativas
ESPERA_BASE_SEGUNDOS = 60


# Pequena pausa após cada ano concluído
PAUSA_ENTRE_ANOS = 5


# ==========================================================
# PREPARAR DIRETÓRIO
# ==========================================================

ERA5_COMPLEMENTO_ANOS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==========================================================
# FUNÇÃO: QUANTIDADE ESPERADA DE MENSAGENS
# ==========================================================

def mensagens_esperadas_ano(ano):
    """
    Cada dia precisa de 6 campos horários:
    00, 01, 02, 03, 22 e 23 UTC.
    """

    dias = (
        366
        if isleap(ano)
        else 365
    )

    return dias * 6


# ==========================================================
# FUNÇÃO: VALIDAR GRIB BAIXADO
# ==========================================================

def validar_grib(
    caminho,
    ano,
):
    """
    Valida estruturalmente o GRIB anual.

    Verifica:
    - quantidade de mensagens;
    - variável mx2t;
    - paramId 201;
    - stepType max;
    - grade 161 x 161;
    - gridType regular_ll;
    - horas válidas esperadas;
    - ano do valid_time.

    Não carrega todos os valores das células em memória.
    """

    print("\nValidando arquivo baixado...")

    esperado = mensagens_esperadas_ano(
        ano
    )

    contador = 0

    horas_encontradas = set()

    problemas = []


    with open(
        caminho,
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

                short_name = codes_get(
                    gid,
                    "shortName",
                )

                param_id = int(
                    codes_get(
                        gid,
                        "paramId",
                    )
                )

                step_type = codes_get(
                    gid,
                    "stepType",
                )

                grid_type = codes_get(
                    gid,
                    "gridType",
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


                horas_encontradas.add(
                    validity_time
                )


                # ------------------------------------------
                # TESTES
                # ------------------------------------------

                if short_name != "mx2t":

                    problemas.append(
                        f"Mensagem {contador}: "
                        f"shortName={short_name}"
                    )


                if param_id != 201:

                    problemas.append(
                        f"Mensagem {contador}: "
                        f"paramId={param_id}"
                    )


                if step_type != "max":

                    problemas.append(
                        f"Mensagem {contador}: "
                        f"stepType={step_type}"
                    )


                if grid_type != "regular_ll":

                    problemas.append(
                        f"Mensagem {contador}: "
                        f"gridType={grid_type}"
                    )


                if nx != 161 or ny != 161:

                    problemas.append(
                        f"Mensagem {contador}: "
                        f"grade={nx}x{ny}"
                    )


                ano_validade = (
                    validity_date
                    // 10000
                )


                if ano_validade != ano:

                    problemas.append(
                        f"Mensagem {contador}: "
                        f"validityDate={validity_date}"
                    )


                if (
                    validity_time
                    not in HORAS_VALIDAS_ESPERADAS
                ):

                    problemas.append(
                        f"Mensagem {contador}: "
                        f"validityTime="
                        f"{validity_time}"
                    )


            finally:

                codes_release(
                    gid
                )


    # ======================================================
    # RESULTADO DA VALIDAÇÃO
    # ======================================================

    print(
        f"Mensagens esperadas: "
        f"{esperado:,}"
    )

    print(
        f"Mensagens encontradas: "
        f"{contador:,}"
    )


    print(
        "Horas encontradas:",
        sorted(
            horas_encontradas
        ),
    )


    quantidade_correta = (
        contador == esperado
    )


    horas_corretas = (
        horas_encontradas
        ==
        HORAS_VALIDAS_ESPERADAS
    )


    sem_problemas = (
        len(problemas) == 0
    )


    aprovado = (
        quantidade_correta
        and horas_corretas
        and sem_problemas
    )


    if aprovado:

        print(
            "\nValidação: APROVADO"
        )

        return True


    print(
        "\nValidação: REPROVADO"
    )


    if not quantidade_correta:

        print(
            "\nQuantidade de mensagens incorreta."
        )


    if not horas_corretas:

        print(
            "\nHoras válidas incorretas."
        )


        print(
            "Esperadas:",
            sorted(
                HORAS_VALIDAS_ESPERADAS
            ),
        )


        print(
            "Encontradas:",
            sorted(
                horas_encontradas
            ),
        )


    if problemas:

        print(
            "\nPrimeiros problemas:"
        )

        for problema in problemas[:20]:

            print(
                " -",
                problema,
            )


        if len(problemas) > 20:

            print(
                f"... e mais "
                f"{len(problemas) - 20} "
                f"problemas."
            )


    return False


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 80)

print(
    "DOWNLOAD DO COMPLEMENTO ERA5 "
    "1995–2025"
)

print("=" * 80)


print("\nHorários complementares:")

for hora in HORAS_FALTANTES:

    print(
        f"  {hora}"
    )


print(
    "\nPeríodo:"
)

print(
    f"  {ANO_INICIAL}–{ANO_FINAL}"
)


print(
    "\nDiretório de destino:"
)

print(
    ERA5_COMPLEMENTO_ANOS_DIR
)


# ==========================================================
# CONTADORES
# ==========================================================

anos_existentes = []

anos_baixados = []

anos_falhos = []


# ==========================================================
# LOOP PRINCIPAL
# ==========================================================

for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):


    print("\n" + "=" * 80)

    print(
        f"ANO {ano}"
    )

    print("=" * 80)


    # ======================================================
    # CAMINHOS
    # ======================================================

    arquivo_final = (
        ERA5_COMPLEMENTO_ANOS_DIR
        / f"mx2t_faltantes_{ano}.grib"
    )


    arquivo_temporario = Path(
        str(
            arquivo_final
        )
        + ".part"
    )


    # ======================================================
    # VERIFICAR SE JÁ EXISTE
    # ======================================================

    if (
        arquivo_final.exists()
        and arquivo_final.stat().st_size > 0
    ):

        print(
            "\nArquivo já existe:"
        )

        print(
            arquivo_final
        )


        tamanho_mb = (
            arquivo_final
            .stat()
            .st_size
            / 1024**2
        )


        print(
            f"Tamanho: "
            f"{tamanho_mb:.2f} MB"
        )


        print(
            "\nValidando arquivo existente..."
        )


        valido = validar_grib(
            arquivo_final,
            ano,
        )


        if valido:

            print(
                "\nArquivo existente é válido."
            )

            print(
                "Pulando download."
            )

            anos_existentes.append(
                ano
            )

            continue


        else:

            print(
                "\nArquivo existente é inválido."
            )

            print(
                "Ele será removido "
                "e baixado novamente."
            )

            arquivo_final.unlink()


    # ======================================================
    # REMOVER .PART ANTIGO
    # ======================================================

    if arquivo_temporario.exists():

        print(
            "\nRemovendo arquivo parcial antigo:"
        )

        print(
            arquivo_temporario
        )

        arquivo_temporario.unlink()


    # ======================================================
    # EXPECTATIVA
    # ======================================================

    dias_ano = (
        366
        if isleap(ano)
        else 365
    )


    esperado = (
        mensagens_esperadas_ano(
            ano
        )
    )


    print(
        f"\nDias no ano: "
        f"{dias_ano}"
    )


    print(
        f"Mensagens esperadas: "
        f"{esperado:,}"
    )


    # ======================================================
    # REQUEST CDS
    # ======================================================

    request = {

        "product_type": [
            "reanalysis"
        ],

        "variable": [
            "maximum_2m_temperature_since_previous_post_processing"
        ],

        "year": [
            str(ano)
        ],

        "month": MESES,

        "day": DIAS,

        "time": HORAS_FALTANTES,

        "data_format": "grib",

        "download_format": "unarchived",

        # Norte, Oeste, Sul, Leste
        "area": [
            6,
            -74,
            -34,
            -34,
        ],

        "grid": [
            0.25,
            0.25,
        ],
    }


    # ======================================================
    # TENTATIVAS
    # ======================================================

    download_concluido = False


    for tentativa in range(
        1,
        MAX_TENTATIVAS + 1,
    ):

        print(
            f"\nTentativa "
            f"{tentativa}/"
            f"{MAX_TENTATIVAS}"
        )


        try:

            # Criar novo cliente a cada tentativa.
            # Isso evita reaproveitar estado de um job
            # que o CDS eventualmente tenha removido.

            cliente = cdsapi.Client()


            print(
                "\nEnviando requisição "
                "ao CDS..."
            )


            resultado = cliente.retrieve(
                DATASET,
                request,
            )


            print(
                "\nRequisição processada."
            )

            print(
                "Iniciando download..."
            )


            resultado.download(
                str(
                    arquivo_temporario
                )
            )


            # ==============================================
            # VERIFICAÇÕES BÁSICAS
            # ==============================================

            if not arquivo_temporario.exists():

                raise RuntimeError(
                    "O arquivo temporário "
                    "não foi criado."
                )


            tamanho = (
                arquivo_temporario
                .stat()
                .st_size
            )


            if tamanho <= 0:

                raise RuntimeError(
                    "O arquivo baixado possui "
                    "tamanho zero."
                )


            tamanho_mb = (
                tamanho
                / 1024**2
            )


            print(
                f"\nDownload recebido:"
            )

            print(
                arquivo_temporario
            )

            print(
                f"Tamanho: "
                f"{tamanho_mb:.2f} MB"
            )


            # ==============================================
            # VALIDAR ANTES DE RENOMEAR
            # ==============================================

            valido = validar_grib(
                arquivo_temporario,
                ano,
            )


            if not valido:

                raise RuntimeError(
                    "O GRIB foi baixado, "
                    "mas falhou na validação."
                )


            # ==============================================
            # RENOMEAR SOMENTE SE TUDO ESTIVER CERTO
            # ==============================================

            arquivo_temporario.rename(
                arquivo_final
            )


            print(
                "\nDOWNLOAD E VALIDAÇÃO "
                "CONCLUÍDOS"
            )


            print(
                "Arquivo definitivo:"
            )

            print(
                arquivo_final
            )


            print(
                f"Tamanho final: "
                f"{arquivo_final.stat().st_size / 1024**2:.2f} MB"
            )


            download_concluido = True

            anos_baixados.append(
                ano
            )

            break


        # ==================================================
        # INTERRUPÇÃO MANUAL
        # ==================================================

        except KeyboardInterrupt:

            print(
                "\n\n" + "=" * 80
            )

            print(
                "DOWNLOAD INTERROMPIDO PELO USUÁRIO"
            )

            print("=" * 80)


            if arquivo_temporario.exists():

                print(
                    "\nRemovendo arquivo parcial:"
                )

                print(
                    arquivo_temporario
                )

                try:

                    arquivo_temporario.unlink()

                except Exception:

                    pass


            print(
                "\nOs arquivos anuais já "
                "concluídos permanecem salvos."
            )

            print(
                "Execute este script novamente "
                "para continuar."
            )

            raise


        # ==================================================
        # OUTROS ERROS
        # ==================================================

        except Exception as erro:

            print(
                "\n" + "-" * 80
            )

            print(
                f"FALHA NA TENTATIVA "
                f"{tentativa}"
            )

            print("-" * 80)


            print(
                f"\nTipo do erro: "
                f"{type(erro).__name__}"
            )


            print(
                "\nMensagem:"
            )

            print(
                erro
            )


            # Arquivo parcial não serve para
            # uma nova tentativa.

            if arquivo_temporario.exists():

                print(
                    "\nRemovendo arquivo parcial:"
                )

                print(
                    arquivo_temporario
                )

                try:

                    arquivo_temporario.unlink()

                except Exception:

                    pass


            # ==============================================
            # ÚLTIMA TENTATIVA
            # ==============================================

            if tentativa == MAX_TENTATIVAS:

                print(
                    "\nNúmero máximo de "
                    "tentativas atingido."
                )

                break


            # ==============================================
            # ESPERA PROGRESSIVA
            # ==============================================

            espera = (
                ESPERA_BASE_SEGUNDOS
                * tentativa
            )


            print(
                f"\nAguardando "
                f"{espera} segundos "
                "antes da próxima tentativa..."
            )


            try:

                time.sleep(
                    espera
                )

            except KeyboardInterrupt:

                print(
                    "\n\nInterrompido pelo usuário."
                )

                raise


    # ======================================================
    # SE TODAS AS TENTATIVAS FALHAREM
    # ======================================================

    if not download_concluido:

        anos_falhos.append(
            ano
        )


        print(
            "\n" + "=" * 80
        )

        print(
            f"NÃO FOI POSSÍVEL "
            f"CONCLUIR {ano}"
        )

        print("=" * 80)


        print(
            "\nO script será interrompido "
            "para evitar enviar dezenas de "
            "requisições enquanto o CDS "
            "pode estar instável."
        )


        print(
            "\nExecute novamente mais tarde."
        )


        break


    # ======================================================
    # PAUSA ENTRE ANOS
    # ======================================================

    if ano < ANO_FINAL:

        print(
            f"\nAguardando "
            f"{PAUSA_ENTRE_ANOS} segundos "
            "antes do próximo ano..."
        )

        time.sleep(
            PAUSA_ENTRE_ANOS
        )


# ==========================================================
# RESUMO FINAL
# ==========================================================

print("\n" + "=" * 80)

print(
    "RESUMO DO PROCESSO"
)

print("=" * 80)


print(
    f"\nAnos já existentes e válidos: "
    f"{len(anos_existentes)}"
)


if anos_existentes:

    print(
        anos_existentes
    )


print(
    f"\nAnos baixados nesta execução: "
    f"{len(anos_baixados)}"
)


if anos_baixados:

    print(
        anos_baixados
    )


print(
    f"\nAnos com falha: "
    f"{len(anos_falhos)}"
)


if anos_falhos:

    print(
        anos_falhos
    )


# ==========================================================
# CONTAGEM DOS ARQUIVOS DEFINITIVOS
# ==========================================================

arquivos_finais = sorted(
    ERA5_COMPLEMENTO_ANOS_DIR.glob(
        "mx2t_faltantes_*.grib"
    )
)


print(
    f"\nArquivos anuais atualmente "
    f"no diretório: "
    f"{len(arquivos_finais)}"
)


# ==========================================================
# RESULTADO
# ==========================================================

if len(arquivos_finais) == (
    ANO_FINAL
    -
    ANO_INICIAL
    +
    1
):

    print("\n" + "=" * 80)

    print(
        "TODOS OS COMPLEMENTOS "
        "1995–2025 ESTÃO PRESENTES"
    )

    print("=" * 80)


    print(
        "\nPróxima etapa:"
    )

    print(
        "validar os 31 anos em conjunto "
        "e construir a camada lógica "
        "ERA5 completa."
    )


else:

    faltam = (
        ANO_FINAL
        -
        ANO_INICIAL
        +
        1
        -
        len(arquivos_finais)
    )


    print("\n" + "=" * 80)

    print(
        "DOWNLOAD AINDA INCOMPLETO"
    )

    print("=" * 80)


    print(
        f"\nAinda faltam "
        f"{faltam} arquivo(s) anual(is)."
    )


    print(
        "\nÉ seguro executar este script "
        "novamente."
    )

    print(
        "Os anos já concluídos e validados "
        "serão automaticamente ignorados."
    )