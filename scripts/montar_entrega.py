"""Monta a pasta da entrega de 02/11 (docs-tcc/08_...): software sem segredos, banco limpo,
especificação final, artigo e resultados da avaliação.

    .venv/Scripts/python scripts/montar_entrega.py

O banco entregue é novo: migrações + disciplina-piloto + usuários de demonstração (senha tutor12345),
com o PLN no modo simulado, para rodar sem credencial. Nenhum dado real de aluno vai junto.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

MVP = Path(__file__).resolve().parent.parent
DOCS = MVP.parent / "docs-tcc"
DESTINO = DOCS / "08_Entrega_02-11_Software_e_Versao_Final" / "1_PARA_O_PROFESSOR"  # depois, zipar o software
SOFTWARE = DESTINO / "software_chatbot_tutor"
RESULTADO = MVP / "avaliacao" / "resultados" / "20261029-154438"

IGNORAR = shutil.ignore_patterns(
    ".venv", "__pycache__", "*.pyc", ".env", ".acessos_locais.txt", ".servidor", "logs", "staticfiles",
    "db.sqlite3", "fila_reprocessamento.*", "resultados", ".pytest_cache",
)


def main():
    if SOFTWARE.exists():
        shutil.rmtree(SOFTWARE)
    shutil.copytree(MVP, SOFTWARE, ignore=IGNORAR)
    proibidos = [p for p in SOFTWARE.rglob("*") if p.name in (".env", ".acessos_locais.txt", "db.sqlite3")]
    assert not proibidos, f"arquivo sensível na cópia: {proibidos}"

    # banco limpo para a entrega
    banco = SOFTWARE / "db.sqlite3"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{banco.as_posix()}", "DEBUG": "1"}
    py = str(MVP / ".venv" / "Scripts" / "python.exe")
    for args in (["migrate", "-v0"], ["carregar_piloto", "--senha", "tutor12345"]):
        subprocess.run([py, "manage.py", *args], cwd=SOFTWARE, env=env, check=True)
    subprocess.run([py, "manage.py", "shell", "-c",
                    "from atendimento.models import ConfiguracaoPLN as C; c=C.atual(); c.provedor='simulado'; "
                    "c.projeto_gcp=''; c.ref_credencial=''; "
                    "c.modelo_interpretar=c.modelo_gerar='gemini-3.5-flash-lite'; c.save()"],
                   cwd=SOFTWARE, env=env, check=True)
    # notas internas do redesenho e bytecode (que grava o caminho local da máquina) não vão
    for p in [SOFTWARE / "design" / "APLICADO.md", *SOFTWARE.rglob("__pycache__")]:
        shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True)

    # resultados da avaliação e do teste de carga
    res = DESTINO / "resultados_avaliacao"
    if res.exists():
        shutil.rmtree(res)
    shutil.copytree(RESULTADO, res / RESULTADO.name)
    for carga in (MVP / "avaliacao" / "resultados").glob("carga-*.json"):
        shutil.copy2(carga, res / carga.name)

    for origem in (DOCS / "00_Documento_Consolidado" / "Especificacao_Chatbot_Tutor_v2026-11-02.pdf",
                   DOCS / "07_Entrega_25-10_Artigo_Cientifico" / "Artigo_Chatbot_Tutor_SBC.pdf"):
        shutil.copy2(origem, DESTINO / origem.name)
    print("entrega montada em", DESTINO)


if __name__ == "__main__":
    sys.exit(main())
