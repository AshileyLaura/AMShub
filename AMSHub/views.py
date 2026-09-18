from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from functools import wraps

from .models import (
    Perfil,
    Aluno,
    Professor,
    Supervisor,
    Empresa,
    Mentoria,
    Participacao,
    Portfolio,
    Certificado,
    Viagem,
    Vaga,
    Horas,
    Notificacao,
    Atividade,
)


def index(request):
    return render(request, 'index.html')


def tipo_permitido(tipo):
    def decorator(view_func):

        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):

            if not hasattr(request.user, 'perfil'):
                return redirect('login')

            if request.user.perfil.tipo != tipo:
                tipo_usuario = request.user.perfil.tipo

                if tipo_usuario == 'aluno':
                    return redirect('aluno')

                elif tipo_usuario == 'professor':
                    return redirect('professor')

                elif tipo_usuario == 'coordenador':
                    return redirect('coordenador')

                elif tipo_usuario == 'supervisor':
                    return redirect('supervisor')

                elif tipo_usuario == 'empresa':
                    return redirect('empresa')

                return redirect('index')

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


@tipo_permitido('aluno')
def aluno(request):

    aluno = get_object_or_404(
        Aluno,
        perfil__user=request.user
    )

    participacoes = Participacao.objects.filter(
        id_aluno=aluno
    )

    horas_mentorias = sum(
        participacao.horas
        for participacao in participacoes
    )

    mentorias = participacoes.values_list(
        'id_mentoria',
        flat=True
    )

    horas_atividades = sum(
        atividade.horas
        for atividade in Atividade.objects.filter(
            id_mentoria__in=mentorias
        )
    )

    horas_certificados = sum(
        certificado.carga_horaria
        for certificado in Certificado.objects.filter(
            id_aluno=aluno
        )
    )

    horas_viagens = sum(
        viagem.horas
        for viagem in Viagem.objects.filter(
            id_aluno=aluno
        )
    )

    horas_complementares = sum(
        hora.quantidade
        for hora in Horas.objects.filter(
            id_aluno=aluno
        )
    )

    total_horas = (
        horas_mentorias
        + horas_atividades
        + horas_certificados
        + horas_viagens
        + horas_complementares
    )

    contexto = {
        'usuario': request.user,
        'aluno': aluno,
        'nome_usuario': request.user.get_full_name() or request.user.username,
        'horas_mentorias': horas_mentorias,
        'horas_atividades': horas_atividades,
        'horas_certificados': horas_certificados,
        'horas_viagens': horas_viagens,
        'horas_complementares': horas_complementares,
        'total_horas': total_horas,
    }

    return render(request, 'Aluno.html', contexto)


@tipo_permitido('professor')
def professor(request):

    contexto = {
        'usuario': request.user,
        'nome_usuario': request.user.get_full_name() or request.user.username,
    }

    return render(request, 'Professor.html', contexto)


@tipo_permitido('coordenador')
def coordenador(request):

    contexto = {
        'usuario': request.user,
        'nome_usuario': request.user.get_full_name() or request.user.username,
    }

    return render(request, 'Coordenador.html', contexto)


@tipo_permitido('supervisor')
def supervisor(request):

    contexto = {
        'usuario': request.user,
        'nome_usuario': request.user.get_full_name() or request.user.username,
    }

    return render(request, 'Supervisor.html', contexto)


@tipo_permitido('empresa')
def empresa(request):

    contexto = {
        'usuario': request.user,
        'nome_usuario': request.user.get_full_name() or request.user.username,
    }

    return render(request, 'Empresa.html', contexto)


def login_view(request):

    pagina = 'loginAluno.html'

    if request.path == '/login/professor/':
        pagina = 'loginProfessor.html'

    elif request.path == '/login/coordenador/':
        pagina = 'loginCoordenador.html'

    elif request.path == '/login/supervisor/':
        pagina = 'loginSupervisor.html'

    elif request.path == '/login/empresa/':
        pagina = 'loginempresa.html'

    if request.method == 'POST':

        username = request.POST.get('username')
        senha = request.POST.get('senha')

        usuario = authenticate(
            request,
            username=username,
            password=senha
        )

        if usuario is not None:

            if not hasattr(usuario, 'perfil'):
                return render(
                    request,
                    pagina,
                    {
                        'erro': 'Este usuário não possui um perfil cadastrado.'
                    }
                )

            tipo = usuario.perfil.tipo

            login(request, usuario)

            if tipo == 'aluno':
                return redirect('aluno')

            elif tipo == 'professor':
                return redirect('professor')

            elif tipo == 'coordenador':
                return redirect('coordenador')

            elif tipo == 'supervisor':
                return redirect('supervisor')

            elif tipo == 'empresa':
                return redirect('empresa')

            return redirect('index')

        return render(
            request,
            pagina,
            {
                'erro': 'Usuário ou senha inválidos.'
            }
        )

    return render(request, pagina)


def logout_view(request):
    logout(request)
    return redirect('login')


@tipo_permitido('aluno')
def minhasmentoriasa(request):

    aluno = get_object_or_404(
        Aluno,
        perfil__user=request.user
    )

    participacoes = Participacao.objects.filter(
        id_aluno=aluno
    ).select_related(
        'id_mentoria',
        'id_mentoria__id_professor',
        'id_mentoria__id_supervisor'
    )

    mentorias = [
        participacao.id_mentoria
        for participacao in participacoes
    ]

    return render(
        request,
        'minhasmentoriasa.html',
        {
            'aluno': aluno,
            'mentorias': mentorias,
            'nome_usuario': request.user.get_full_name() or request.user.username
        }
    )


@tipo_permitido('aluno')
def detalhesdamentoriaa(request, id_mentoria):

    aluno = get_object_or_404(
        Aluno,
        perfil__user=request.user
    )

    participacao = get_object_or_404(
        Participacao,
        id_aluno=aluno,
        id_mentoria_id=id_mentoria
    )

    mentoria = participacao.id_mentoria

    return render(
        request,
        'detalhesdamentoriaa.html',
        {
            'aluno': aluno,
            'mentoria': mentoria,
            'participacao': participacao,
            'nome_usuario': request.user.get_full_name() or request.user.username
        }
    )


def CEportifoliosa(request):
    return render(request, 'aluno/CEportifoliosa.html')


def meuperfila(request):
    return render(request, 'aluno/meuperfila.html')


@tipo_permitido('aluno')
def meusportifoliosa(request):

    aluno = get_object_or_404(
        Aluno,
        perfil__user=request.user
    )

    portfolios = Portfolio.objects.filter(
        id_aluno=aluno
    ).select_related(
        'id_mentoria'
    )

    return render(
        request,
        'aluno/meusportifoliosa.html',
        {
            'aluno': aluno,
            'portfolios': portfolios,
            'nome_usuario': request.user.get_full_name() or request.user.username
        }
    )


@tipo_permitido('aluno')
def atividadesa(request):

    aluno = get_object_or_404(
        Aluno,
        perfil__user=request.user
    )

    participacoes = Participacao.objects.filter(
        id_aluno=aluno
    ).values_list(
        'id_mentoria',
        flat=True
    )

    atividades = Atividade.objects.filter(
        id_mentoria__in=participacoes
    ).select_related(
        'id_mentoria'
    )

    return render(
        request,
        'aluno/atividadesa.html',
        {
            'aluno': aluno,
            'atividades': atividades,
            'nome_usuario': request.user.get_full_name() or request.user.username
        }
    )


def pendenciasa(request):
    return render(request, 'aluno/pendenciasa.html')


@tipo_permitido('aluno')
def certificadoa(request):

    aluno = get_object_or_404(
        Aluno,
        perfil__user=request.user
    )

    certificados = Certificado.objects.filter(
        id_aluno=aluno
    )

    return render(
        request,
        'aluno/certificadoa.html',
        {
            'aluno': aluno,
            'certificados': certificados,
            'nome_usuario': request.user.get_full_name() or request.user.username
        }
    )


def detalhesdaatividadea(request):
    return render(request, 'aluno/detalhesdaatividadea.html')

def meuperfila(request):
    return render(request, 'aluno/meuperfila.html')


def cadastro(request):

    if request.method == 'POST':

        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '').strip()
        tipo = request.POST.get('tipo', '').strip().lower()
        curso = request.POST.get('curso', '').strip()
        rm = request.POST.get('rm', '').strip()

        tipos_validos = [
            'aluno',
            'professor',
            'coordenador',
            'supervisor',
            'empresa'
        ]

        if tipo not in tipos_validos:
            return render(
                request,
                'cadastro.html',
                {'erro': 'Tipo de usuário inválido.'}
            )

        if User.objects.filter(username=email).exists():
            return render(
                request,
                'cadastro.html',
                {'erro': 'Este e-mail já está cadastrado.'}
            )

        usuario = User.objects.create_user(
            username=email,
            email=email,
            password=senha,
            first_name=nome
        )

        perfil = Perfil.objects.create(
            user=usuario,
            tipo=tipo
        )

        if tipo == 'aluno':
            Aluno.objects.create(
                perfil=perfil,
                curso=curso or 'Não informado',
                turma=rm or 'Não informado'
            )

        elif tipo == 'professor':
            Professor.objects.create(
                perfil=perfil
            )

        elif tipo == 'supervisor':
            Supervisor.objects.create(
                perfil=perfil
            )

        elif tipo == 'empresa':
            Empresa.objects.create(
                perfil=perfil,
                nome=nome
            )

        return redirect('login')

    return render(request, 'cadastro.html')