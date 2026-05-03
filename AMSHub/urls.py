from django.urls import path
from AMSHub.views import (
    index, aluno, professor, coordenador, supervisor,
    login_aluno, login_professor, login_coordenador, login_supervisor
)

urlpatterns = [
    path('', index, name='index'),

    # TELAS PRINCIPAIS
    path('aluno/', aluno, name='aluno'),
    path('professor/', professor, name='professor'),
    path('coordenador/', coordenador, name='coordenador'),
    path('supervisor/', supervisor, name='supervisor'),

    # LOGIN
    path('login/aluno/', login_aluno, name='login_aluno'),
    path('login/professor/', login_professor, name='login_professor'),
    path('login/coordenador/', login_coordenador, name='login_coordenador'),
    path('login/supervisor/', login_supervisor, name='login_supervisor'),
]