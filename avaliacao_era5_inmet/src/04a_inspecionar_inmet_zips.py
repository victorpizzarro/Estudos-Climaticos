from pathlib import Path
import csv
import io
import zipfile
from collections import Counter

import pandas as pd

from config import PROJECT_DIR


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

ANO_INICIAL = 2000
ANO_FINAL = 2025


INMET_AUTO_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "inmet"
    / "automaticas"
)


TABLES_DIR = (
    PROJECT_DIR
    / "outputs"
    / "tables"
)


LOGS_DIR = (
    PROJECT_DIR
    / "outputs"
    / "logs"
)


TABLES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


LOGS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ARQUIVO_INVENTARIO = (
    TABLES_DIR
    / "inventario_inmet_zips.csv"
)


ARQUIVO_LOG = (
    LOGS_DIR
    / "inspecao_inmet_amostras.txt"
)


# Anos que queremos examinar mais profundamente.
# Se algum não existir, o script simplesmente informa.
ANOS_AMOSTRA = [
    2000,
    2010,
    2020,
    2025,
]


# Número máximo de linhas iniciais que serão lidas
# de cada arquivo de amostra.
MAX_LINHAS_AMOSTRA = 30


# ==========================================================
# FUNÇÕES
# ==========================================================

def tentar_decodificar(dados):
    """
    Tenta algumas codificações comuns nos arquivos do INMET.
    """

    codificacoes = [
        "utf-8-sig",
        "utf-8",
        "latin-1",
        "cp1252",
    ]

    for encoding in codificacoes:

        try:

            texto = dados.decode(
                encoding
            )

            return (
                texto,
                encoding,
            )

        except UnicodeDecodeError:

            continue


    return (
        dados.decode(
            "latin-1",
            errors="replace",
        ),
        "latin-1-com-replace",
    )


def detectar_separador(linhas):
    """
    Tenta descobrir o separador do arquivo.
    """

    texto = "\n".join(
        linhas[:20]
    )


    candidatos = [
        ";",
        ",",
        "\t",
        "|",
    ]


    try:

        dialect = csv.Sniffer().sniff(
            texto,
            delimiters=candidatos,
        )

        return dialect.delimiter

    except csv.Error:

        # O INMET historicamente usa bastante ';'.
        contagens = {
            separador: texto.count(
                separador
            )
            for separador in candidatos
        }

        return max(
            contagens,
            key=contagens.get,
        )


def localizar_cabecalho(linhas):
    """
    Procura a linha que parece conter os nomes
    das colunas da série horária.
    """

    palavras_chave = [
        "DATA",
        "HORA",
        "TEMPERATURA",
        "PRECIPITA",
        "PRESSAO",
        "UMIDADE",
    ]


    for indice, linha in enumerate(
        linhas
    ):

        linha_upper = (
            linha
            .upper()
            .strip()
        )


        pontuacao = sum(
            palavra in linha_upper
            for palavra in palavras_chave
        )


        # Normalmente a linha das colunas contém
        # diversas dessas palavras.
        if pontuacao >= 2:

            return indice


    return None


def listar_colunas(
    linha_cabecalho,
    separador,
):
    """
    Divide a linha do cabeçalho em colunas.
    """

    reader = csv.reader(
        [linha_cabecalho],
        delimiter=separador,
    )


    colunas = next(
        reader
    )


    return [
        coluna.strip()
        for coluna in colunas
        if coluna.strip()
    ]


def escolher_arquivo_amostra(
    nomes,
):
    """
    Escolhe o primeiro arquivo de dados válido
    dentro do ZIP.
    """

    extensoes_preferidas = (
        ".csv",
        ".txt",
    )


    candidatos = []


    for nome in nomes:

        nome_lower = (
            nome.lower()
        )


        if nome.endswith("/"):
            continue


        if nome_lower.endswith(
            extensoes_preferidas
        ):

            candidatos.append(
                nome
            )


    if not candidatos:

        return None


    return sorted(
        candidatos
    )[0]


def ler_amostra_zip(
    caminho_zip,
):
    """
    Lê uma pequena amostra do primeiro arquivo
    de dados encontrado dentro do ZIP.
    """

    with zipfile.ZipFile(
        caminho_zip,
        "r",
    ) as zf:

        nomes = zf.namelist()


        arquivo_amostra = (
            escolher_arquivo_amostra(
                nomes
            )
        )


        if arquivo_amostra is None:

            return None


        with zf.open(
            arquivo_amostra
        ) as arquivo:

            # 128 KB são mais do que suficientes
            # para cabeçalho + primeiras linhas.
            dados = arquivo.read(
                128 * 1024
            )


    texto, encoding = (
        tentar_decodificar(
            dados
        )
    )


    linhas = texto.splitlines()


    linhas = linhas[
        :MAX_LINHAS_AMOSTRA
    ]


    separador = detectar_separador(
        linhas
    )


    indice_cabecalho = (
        localizar_cabecalho(
            linhas
        )
    )


    if indice_cabecalho is not None:

        colunas = listar_colunas(
            linhas[
                indice_cabecalho
            ],
            separador,
        )

    else:

        colunas = []


    return {
        "arquivo":
            arquivo_amostra,

        "encoding":
            encoding,

        "separador":
            separador,

        "indice_cabecalho":
            indice_cabecalho,

        "linhas":
            linhas,

        "colunas":
            colunas,
    }


# ==========================================================
# CABEÇALHO
# ==========================================================

print("=" * 90)

print(
    "INSPEÇÃO DOS ARQUIVOS HISTÓRICOS DO INMET"
)

print("=" * 90)


print(
    "\nDiretório analisado:"
)

print(
    INMET_AUTO_DIR
)


# ==========================================================
# VERIFICAR DIRETÓRIO
# ==========================================================

if not INMET_AUTO_DIR.exists():

    raise FileNotFoundError(
        "Diretório das estações automáticas "
        "não encontrado:\n"
        f"{INMET_AUTO_DIR}"
    )


# ==========================================================
# 1. INVENTÁRIO DOS ANOS
# ==========================================================

print("\n" + "=" * 90)

print(
    "INVENTÁRIO DOS ANOS"
)

print("=" * 90)


inventario = []

anos_presentes = []

anos_ausentes = []


for ano in range(
    ANO_INICIAL,
    ANO_FINAL + 1,
):

    arquivo_zip = (
        INMET_AUTO_DIR
        / f"{ano}.zip"
    )


    if not arquivo_zip.exists():

        print(
            f"{ano}: AUSENTE"
        )

        anos_ausentes.append(
            ano
        )

        inventario.append(
            {
                "ano": ano,
                "arquivo": "",
                "tamanho_mb": "",
                "arquivos_internos": 0,
                "csv": 0,
                "txt": 0,
                "outros": 0,
                "status": "AUSENTE",
            }
        )

        continue


    anos_presentes.append(
        ano
    )


    tamanho_mb = (
        arquivo_zip.stat().st_size
        /
        1024**2
    )


    try:

        with zipfile.ZipFile(
            arquivo_zip,
            "r",
        ) as zf:

            nomes = [
                nome
                for nome
                in zf.namelist()
                if not nome.endswith("/")
            ]


            extensoes = Counter(
                Path(nome)
                .suffix
                .lower()
                for nome in nomes
            )


            qtd_csv = (
                extensoes.get(
                    ".csv",
                    0,
                )
            )


            qtd_txt = (
                extensoes.get(
                    ".txt",
                    0,
                )
            )


            qtd_outros = (
                len(nomes)
                -
                qtd_csv
                -
                qtd_txt
            )


            status = "OK"


    except zipfile.BadZipFile:

        nomes = []

        qtd_csv = 0
        qtd_txt = 0
        qtd_outros = 0

        status = "ZIP_CORROMPIDO"


    print(
        f"{ano}: "
        f"{tamanho_mb:8.2f} MB | "
        f"{len(nomes):4d} arquivos | "
        f"CSV={qtd_csv} | "
        f"TXT={qtd_txt} | "
        f"{status}"
    )


    inventario.append(
        {
            "ano":
                ano,

            "arquivo":
                arquivo_zip.name,

            "tamanho_mb":
                round(
                    tamanho_mb,
                    2,
                ),

            "arquivos_internos":
                len(nomes),

            "csv":
                qtd_csv,

            "txt":
                qtd_txt,

            "outros":
                qtd_outros,

            "status":
                status,
        }
    )


# ==========================================================
# 2. SALVAR INVENTÁRIO
# ==========================================================

df_inventario = pd.DataFrame(
    inventario
)


df_inventario.to_csv(
    ARQUIVO_INVENTARIO,
    index=False,
    encoding="utf-8",
)


print(
    "\nInventário salvo em:"
)

print(
    ARQUIVO_INVENTARIO
)


# ==========================================================
# 3. VISÃO DOS NOMES INTERNOS
# ==========================================================

print("\n" + "=" * 90)

print(
    "PADRÃO DOS NOMES DOS ARQUIVOS INTERNOS"
)

print("=" * 90)


for ano in anos_presentes[:3]:

    arquivo_zip = (
        INMET_AUTO_DIR
        / f"{ano}.zip"
    )


    print(
        f"\nANO {ano}"
    )


    with zipfile.ZipFile(
        arquivo_zip,
        "r",
    ) as zf:

        nomes = [
            nome
            for nome
            in zf.namelist()
            if not nome.endswith("/")
        ]


        print(
            f"Total: {len(nomes)}"
        )


        print(
            "\nPrimeiros arquivos:"
        )


        for nome in nomes[:10]:

            print(
                " ",
                nome,
            )


# ==========================================================
# 4. INSPEÇÃO PROFUNDA DE ANOS REPRESENTATIVOS
# ==========================================================

print("\n" + "=" * 90)

print(
    "INSPEÇÃO DE AMOSTRAS"
)

print("=" * 90)


log = []


for ano in ANOS_AMOSTRA:

    arquivo_zip = (
        INMET_AUTO_DIR
        / f"{ano}.zip"
    )


    print("\n" + "-" * 90)

    print(
        f"ANO {ano}"
    )

    print("-" * 90)


    log.append(
        "=" * 90
    )

    log.append(
        f"ANO {ano}"
    )

    log.append(
        "=" * 90
    )


    if not arquivo_zip.exists():

        texto = (
            f"Arquivo {ano}.zip não encontrado."
        )

        print(
            texto
        )

        log.append(
            texto
        )

        continue


    try:

        resultado = (
            ler_amostra_zip(
                arquivo_zip
            )
        )

    except zipfile.BadZipFile:

        texto = (
            "ZIP corrompido."
        )

        print(
            texto
        )

        log.append(
            texto
        )

        continue


    if resultado is None:

        texto = (
            "Nenhum arquivo CSV/TXT "
            "foi encontrado."
        )

        print(
            texto
        )

        log.append(
            texto
        )

        continue


    print(
        "\nArquivo usado como amostra:"
    )

    print(
        resultado[
            "arquivo"
        ]
    )


    print(
        f"\nEncoding detectado: "
        f"{resultado['encoding']}"
    )


    print(
        "Separador provável: "
        f"{repr(resultado['separador'])}"
    )


    print(
        "Linha provável do cabeçalho: "
        f"{resultado['indice_cabecalho']}"
    )


    log.append(
        f"Arquivo: "
        f"{resultado['arquivo']}"
    )

    log.append(
        f"Encoding: "
        f"{resultado['encoding']}"
    )

    log.append(
        f"Separador: "
        f"{repr(resultado['separador'])}"
    )

    log.append(
        f"Índice do cabeçalho: "
        f"{resultado['indice_cabecalho']}"
    )


    # ======================================================
    # LINHAS INICIAIS
    # ======================================================

    print(
        "\nPrimeiras linhas:"
    )


    log.append(
        ""
    )

    log.append(
        "PRIMEIRAS LINHAS:"
    )


    for indice, linha in enumerate(
        resultado[
            "linhas"
        ][:15]
    ):

        texto = (
            f"{indice:02d}: "
            f"{linha}"
        )

        print(
            texto
        )

        log.append(
            texto
        )


    # ======================================================
    # COLUNAS
    # ======================================================

    print(
        "\nColunas detectadas:"
    )


    log.append(
        ""
    )

    log.append(
        "COLUNAS DETECTADAS:"
    )


    if resultado[
        "colunas"
    ]:

        for indice, coluna in enumerate(
            resultado[
                "colunas"
            ]
        ):

            texto = (
                f"{indice:02d}: "
                f"{coluna}"
            )

            print(
                texto
            )

            log.append(
                texto
            )

    else:

        print(
            "Não foi possível detectar."
        )

        log.append(
            "Não foi possível detectar."
        )


    log.append(
        ""
    )


# ==========================================================
# 5. SALVAR LOG
# ==========================================================

ARQUIVO_LOG.write_text(
    "\n".join(
        log
    ),
    encoding="utf-8",
)


print("\n" + "=" * 90)

print(
    "RESUMO"
)

print("=" * 90)


print(
    f"\nAnos esperados: "
    f"{ANO_FINAL - ANO_INICIAL + 1}"
)


print(
    f"Anos presentes: "
    f"{len(anos_presentes)}"
)


print(
    f"Anos ausentes: "
    f"{len(anos_ausentes)}"
)


if anos_ausentes:

    print(
        "\nAnos ausentes:"
    )

    print(
        anos_ausentes
    )


print(
    "\nLog detalhado salvo em:"
)

print(
    ARQUIVO_LOG
)


print(
    "\nInventário salvo em:"
)

print(
    ARQUIVO_INVENTARIO
)


print("\n" + "=" * 90)

print(
    "INSPEÇÃO CONCLUÍDA"
)

print("=" * 90)