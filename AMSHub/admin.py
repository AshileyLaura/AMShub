from django.contrib import admin

from .models import (
    Perfil,
    Aluno,
    Professor,
    Supervisor,
    Empresa,
    Mentoria,
    Atividade,
    Participacao,
    Portfolio,
    Certificado,
    Viagem,
    Vaga,
    Horas,
    Notificacao,
)


for modelo in (
    Perfil,
    Aluno,
    Professor,
    Supervisor,
    Empresa,
    Mentoria,
    Atividade,
    Participacao,
    Portfolio,
    Certificado,
    Viagem,
    Vaga,
    Horas,
    Notificacao,
):
    admin.site.register(modelo)