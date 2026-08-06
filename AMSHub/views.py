from django.shortcuts import render, redirect

def index(request):
    return render(request, 'index.html')

def aluno(request):
    return render(request, 'Aluno.html')

def professor(request):
    return render(request, 'Professor.html')

def coordenador(request):
    return render(request, 'Coordenador.html')

def supervisor(request):
    return render(request, 'Supervisor.html')

def empresa(request):
    return render(request, 'Empresa.html')


def login_aluno(request):
    if request.method == "POST":
        email = request.POST.get("email")
        senha = request.POST.get("senha")

        if email == "aluno@gmail.com" and senha == "123":
            return redirect('aluno')

    return render(request, 'loginAluno.html')


def login_professor(request):
    if request.method == "POST":
        email = request.POST.get("email")
        senha = request.POST.get("senha")

        if email == "professor@gmail.com" and senha == "123":
            return redirect('professor')
    return render(request, 'loginProfessor.html')


def login_coordenador(request):
    if request.method == "POST":
        email = request.POST.get("email")
        senha = request.POST.get("senha")

        if email == "coordenador@gmail.com" and senha == "123":
            return redirect('coordenador')
    return render(request, 'loginCoordenador.html')


def login_supervisor(request):
    if request.method == "POST":
        email = request.POST.get("email")
        senha = request.POST.get("senha")

        if email == "supervisor@gmail.com" and senha == "123":
            return redirect('supervisor')
    return render(request, 'loginSupervisor.html')

def login_empresa(request):
    if request.method == "POST":
        email = request.POST.get("email")
        senha = request.POST.get("senha")

        if email == "empresa@gmail.com" and senha == "123":
            return redirect('empresa')
    return render(request, 'loginempresa.html')