from django.db import migrations, models

import academico.models


def preencher(apps, schema_editor):
    Turma = apps.get_model("academico", "Turma")
    usados = set()
    for turma in Turma.objects.all():
        codigo = academico.models.gerar_codigo_convite()
        while codigo in usados:
            codigo = academico.models.gerar_codigo_convite()
        usados.add(codigo)
        turma.codigo_convite = codigo
        turma.save(update_fields=["codigo_convite"])


class Migration(migrations.Migration):
    dependencies = [("academico", "0002_initial")]

    operations = [
        migrations.AddField(
            model_name="turma", name="codigo_convite",
            field=models.CharField("código de convite", max_length=12, null=True),
        ),
        migrations.RunPython(preencher, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="turma", name="codigo_convite",
            field=models.CharField(
                "código de convite", max_length=12, unique=True, default=academico.models.gerar_codigo_convite,
                help_text="O aluno informa este código ao se cadastrar e entra direto na turma.",
            ),
        ),
        migrations.AddField(
            model_name="turma", name="cadastro_aberto",
            field=models.BooleanField(default=True, verbose_name="cadastro pelo código aberto"),
        ),
    ]
