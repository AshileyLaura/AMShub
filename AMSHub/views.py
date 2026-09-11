from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from functools import wraps
from .models import Mentoria


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

    contexto = {
        'usuario': request.user,
        'nome_usuario': request.user.get_full_name() or request.user.username,
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


@login_required
def minhasmentoriasa(request):

    mentorias = Mentoria.objects.all().order_by('data')

    return render(
        request,
        'aluno/minhasmentoriasa.html',
        {
            'mentorias': mentorias
        }
    )


def CEportifoliosa(request):
    return render(request, 'aluno/CEportifoliosa.html')


def detalhesdamentoriaa(request):
    return render(request, 'aluno/detalhesdamentoriaa.html')


def meuperfila(request):
    return render(request, 'aluno/meuperfila.html')


def meusportifoliosa(request):
    return render(request, 'aluno/meusportifoliosa.html')