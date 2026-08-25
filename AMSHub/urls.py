from django.urls import path
from AMSHub.views import (
    index,
    aluno,
    professor,
    coordenador,
    supervisor,
    empresa,
    login_view,
    logout_view,
)

urlpatterns = [
    path('', index, name='index'),

    # TELAS PRINCIPAIS
    path('aluno/', aluno, name='aluno'),
    path('professor/', professor, name='professor'),
    path('coordenador/', coordenador, name='coordenador'),
    path('supervisor/', supervisor, name='supervisor'),
    path('empresa/', empresa, name='empresa'),

    # LOGIN
    path('login/', login_view, name='login'),

    path('login/aluno/', login_view, name='login_aluno'),
    path('login/professor/', login_view, name='login_professor'),
    path('login/coordenador/', login_view, name='login_coordenador'),
    path('login/supervisor/', login_view, name='login_supervisor'),
    path('login/empresa/', login_view, name='login_empresa'),

    # LOGOUT
    path('logout/', logout_view, name='logout'),
]
