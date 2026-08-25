from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


def index(request):
    return render(request, 'index.html')


@login_required
def aluno(request):
    return render(request, 'Aluno.html')


@login_required
def professor(request):
    return render(request, 'Professor.html')


@login_required
def coordenador(request):
    return render(request, 'Coordenador.html')


@login_required
def supervisor(request):
    return render(request, 'Supervisor.html')


@login_required
def empresa(request):
    return render(request, 'Empresa.html')


def login_view(request):

    # Define qual página de login será exibida
    pagina = 'loginAluno.html'

    if request.path == '/login/professor/':
        pagina = 'loginProfessor.html'

    elif request.path == '/login/coordenador/':
        pagina = 'loginCoordenador.html'

    elif request.path == '/login/supervisor/':
        pagina = 'loginSupervisor.html'

    elif request.path == '/login/empresa/':
        pagina = 'loginempresa.html'

    # Quando o formulário for enviado
    if request.method == 'POST':

        username = request.POST.get('username')
        senha = request.POST.get('senha')

        # Django verifica usuário e senha
        usuario = authenticate(
            request,
            username=username,
            password=senha
        )

        if usuario is not None:

            # Cria a sessão do usuário
            login(request, usuario)

            # Verifica se o usuário possui um Perfil
            if hasattr(usuario, 'perfil'):

                tipo = usuario.perfil.tipo

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

            # Caso o usuário não tenha perfil
            return redirect('index')

        # Usuário ou senha incorretos
        return render(
            request,
            pagina,
            {
                'erro': 'Usuário ou senha inválidos.'
            }
        )

    # Primeira vez abrindo a página
    return render(request, pagina)


def logout_view(request):
    logout(request)
    return redirect('login')
