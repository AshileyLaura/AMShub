from django.db import migrations
from django.contrib.auth.hashers import make_password


def criar_manuela(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Perfil = apps.get_model('AMSHub', 'Perfil')
    Aluno = apps.get_model('AMSHub', 'Aluno')

    usuario, criado = User.objects.get_or_create(
        username='manuela'
    )

    usuario.first_name = 'Manuela'
    usuario.password = make_password('123')
    usuario.save()

    perfil, criado = Perfil.objects.get_or_create(
        user=usuario,
        defaults={'tipo': 'aluno'}
    )

    if perfil.tipo != 'aluno':
        perfil.tipo = 'aluno'
        perfil.save()

    Aluno.objects.get_or_create(
        perfil=perfil,
        defaults={
            'curso': 'Não informado',
            'turma': 'Não informado'
        }
    )


def remover_manuela(apps, schema_editor):
    User = apps.get_model('auth', 'User')

    User.objects.filter(
        username='manuela'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('AMSHub', '0002_criar_usuarios_teste'),
    ]

    operations = [
        migrations.RunPython(
            criar_manuela,
            remover_manuela
        ),
    ]