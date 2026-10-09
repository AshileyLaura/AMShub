from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from django.utils import timezone
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
# ---------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------
# Status de atividade que contam como "concluída".
# Qualquer outro status (ex.: "Pendente") é tratado como não concluída.
STATUS_CONCLUIDO = ('concluída', 'concluida', 'concluído', 'concluido')
def nome_do_usuario(request):
    return request.user.get_full_name() or request.user.username
def obter_aluno(request):
    return get_object_or_404(
        Aluno,
        perfil__user=request.user
    )
def atividades_do_aluno(aluno):
    """Atividades das mentorias em que o aluno participa."""
    mentorias = Participacao.objects.filter(
        id_aluno=aluno
    ).values_list(
        'id_mentoria',
        flat=True
    )
    return Atividade.objects.filter(
        id_mentoria__in=mentorias
    ).select_related(
        'id_mentoria__id_professor__perfil__user',
        'id_mentoria__id_supervisor__perfil__user'
    ).order_by(
        'data_entrega',
        'id_atividade'
    )
def atividade_concluida(atividade):
    return (atividade.status or '').strip().lower() in STATUS_CONCLUIDO
def classificar_atividades(atividades, hoje):
    """Separa as atividades em pendentes, concluídas e em atraso."""
    pendentes = []
    concluidas = []
    atrasadas = []
    for atividade in atividades:
        if atividade_concluida(atividade):
            concluidas.append(atividade)
        elif atividade.data_entrega and atividade.data_entrega < hoje:
            atrasadas.append(atividade)
        else:
            pendentes.append(atividade)
    return pendentes, concluidas, atrasadas
def situacao_atividade(atividade, hoje):
    """Devolve (classe_css, texto) da situação de uma atividade."""
    if atividade_concluida(atividade):
        return 'concluida', 'Concluída'
    if atividade.data_entrega and atividade.data_entrega < hoje:
        return 'atraso', 'Em atraso'
    return 'pendente', 'Pendente'
def classe_certificado(status):
    """Converte o texto do status do certificado em classe do CSS."""
    texto = (status or '').strip().lower()
    if texto.startswith('aprov'):
        return 'aprovado'
    if 'anális' in texto or 'analis' in texto:
        return 'analise'
    return 'pendente'
def portfolio_pendente(portfolio):
    return (portfolio.status or '').strip().lower() == 'pendente'
def montar_pendencias(aluno, hoje):
    """Monta as listas da tela de pendências a partir do banco."""
    pendentes, _, atrasadas = classificar_atividades(
        atividades_do_aluno(aluno),
        hoje
    )
    em_atraso = []
    proximas = []
    outras = []
    for atividade in atrasadas:
        em_atraso.append({
            'titulo': atividade.titulo,
            'tipo': 'Atividade',
            'descricao': atividade.descricao,
            'prazo': atividade.data_entrega,
            'dias': (hoje - atividade.data_entrega).days,
            'url': reverse(
                'detalhesdaatividadea',
                args=[atividade.id_atividade]
            ),
        })
    for atividade in pendentes:
        item = {
            'titulo': atividade.titulo,
            'tipo': 'Atividade',
            'descricao': atividade.descricao,
            'prazo': atividade.data_entrega,
            'dias': None,
            'url': reverse(
                'detalhesdaatividadea',
                args=[atividade.id_atividade]
            ),
        }
        if atividade.data_entrega:
            item['dias'] = (atividade.data_entrega - hoje).days
            proximas.append(item)
        else:
            outras.append(item)
    for certificado in Certificado.objects.filter(id_aluno=aluno):
        if classe_certificado(certificado.status) == 'pendente':
            outras.append({
                'titulo': certificado.curso,
                'tipo': 'Certificado',
                'descricao': certificado.instituicao,
                'prazo': None,
                'dias': None,
                'url': reverse('certificadoa'),
            })
    portfolios = Portfolio.objects.filter(
        id_aluno=aluno
    ).select_related('id_mentoria')
    for portfolio in portfolios:
        if portfolio_pendente(portfolio):
            outras.append({
                'titulo': portfolio.id_mentoria.tema,
                'tipo': 'Portfólio',
                'descricao': portfolio.resumo,
                'prazo': None,
                'dias': None,
                'url': reverse('meusportifoliosa'),
            })
    return em_atraso, proximas, outras
def redirecionar_por_tipo(tipo):
    destinos = {
        'aluno': 'aluno',
        'professor': 'professor',
        'coordenador': 'coordenador',
        'supervisor': 'supervisor',
        'empresa': 'empresa',
    }
    return redirect(destinos.get(tipo, 'index'))
def tipos_permitidos(*tipos):
    """Libera a tela para um ou mais tipos de usuário."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request.user, 'perfil'):
                return redirect('login')
            if request.user.perfil.tipo not in tipos:
                return redirecionar_por_tipo(request.user.perfil.tipo)
            return view_func(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator
def tipo_permitido(tipo):
    return tipos_permitidos(tipo)
def index(request):
    return render(request, 'index.html')
# ---------------------------------------------------------------------
# FUNÇÕES AUXILIARES DA GESTÃO (coordenador e supervisor)
# ---------------------------------------------------------------------
CARGOS = {
    'coordenador': 'Coordenador',
    'supervisor': 'Supervisor',
}
def resumo_do_aluno(aluno, hoje):
    """Devolve (total de horas, tem atividade em atraso) de um aluno."""
    _, concluidas, atrasadas = classificar_atividades(
        atividades_do_aluno(aluno),
        hoje
    )
    horas = (
        sum(p.horas for p in Participacao.objects.filter(
            id_aluno=aluno, presenca=True))
        + sum(a.horas for a in concluidas)
        + sum(c.carga_horaria for c in Certificado.objects.filter(
            id_aluno=aluno) if classe_certificado(c.status) == 'aprovado')
        + sum(v.horas for v in Viagem.objects.filter(id_aluno=aluno))
        + sum(h.quantidade for h in Horas.objects.filter(id_aluno=aluno))
    )
    return horas, bool(atrasadas)
def contexto_gestao(request):
    """Dados que o gestao.html (base) precisa em qualquer tela de gestão."""
    hoje = timezone.localdate()
    return {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'cargo_usuario': CARGOS.get(request.user.perfil.tipo, ''),
        'total_empresas': Empresa.objects.count(),
        'total_mentorias': Mentoria.objects.count(),
        'empresas_recentes': Empresa.objects.order_by('nome')[:3],
        'proximas_mentorias': Mentoria.objects.filter(
            data__gte=hoje
        ).select_related('empresa').order_by('data')[:3],
    }
# ---------------------------------------------------------------------
# TELAS PRINCIPAIS
# ---------------------------------------------------------------------
@tipo_permitido('aluno')
def aluno(request):
    aluno = obter_aluno(request)
    hoje = timezone.localdate()
    atividades = list(atividades_do_aluno(aluno))
    pendentes, concluidas, atrasadas = classificar_atividades(
        atividades,
        hoje
    )
    # Horas contabilizadas
    horas_mentorias = sum(
        participacao.horas
        for participacao in Participacao.objects.filter(
            id_aluno=aluno,
            presenca=True
        )
    )
    horas_atividades = sum(
        atividade.horas
        for atividade in concluidas
    )
    certificados = list(
        Certificado.objects.filter(id_aluno=aluno)
    )
    horas_certificados = sum(
        certificado.carga_horaria
        for certificado in certificados
        if classe_certificado(certificado.status) == 'aprovado'
    )
    horas_viagens = sum(
        viagem.horas
        for viagem in Viagem.objects.filter(id_aluno=aluno)
    )
    horas_complementares = sum(
        hora.quantidade
        for hora in Horas.objects.filter(id_aluno=aluno)
    )
    total_horas = (
        horas_mentorias
        + horas_atividades
        + horas_certificados
        + horas_viagens
        + horas_complementares
    )
    # Cards do dashboard
    certificados_pendentes = sum(
        1 for certificado in certificados
        if classe_certificado(certificado.status) != 'aprovado'
    )
    horas_pendentes = sum(
        atividade.horas
        for atividade in pendentes + atrasadas
    )
    atividades_mes = sum(
        1 for atividade in atividades
        if atividade.data_entrega
        and atividade.data_entrega.year == hoje.year
        and atividade.data_entrega.month == hoje.month
    )
    ultimas_atividades = sorted(
        concluidas,
        key=lambda atividade: atividade.id_atividade,
        reverse=True
    )[:5]
    contexto = {
        'usuario': request.user,
        'aluno': aluno,
        'nome_usuario': nome_do_usuario(request),
        'horas_mentorias': horas_mentorias,
        'horas_atividades': horas_atividades,
        'horas_certificados': horas_certificados,
        'horas_viagens': horas_viagens,
        'horas_complementares': horas_complementares,
        'total_horas': total_horas,
        'certificados_pendentes': certificados_pendentes,
        'horas_pendentes': horas_pendentes,
        'atividades_mes': atividades_mes,
        'ultimas_atividades': ultimas_atividades,
    }
    return render(request, 'Aluno.html', contexto)
@tipo_permitido('professor')
def professor(request):
    contexto = {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
    }
    return render(request, 'Professor.html', contexto)
@tipo_permitido('empresa')
def empresa(request):
    contexto = {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
    }
    return render(request, 'Empresa.html', contexto)
# ---------------------------------------------------------------------
# GESTÃO: COORDENADOR E SUPERVISOR
# ---------------------------------------------------------------------
@tipos_permitidos('coordenador')
def coordenador(request):
    hoje = timezone.localdate()
    alunos = Aluno.objects.all()
    contexto = contexto_gestao(request)
    contexto['total_alunos'] = alunos.count()
    contexto['alunos_pendentes'] = sum(
        1 for a in alunos if resumo_do_aluno(a, hoje)[1]
    )
    return render(request, 'Coordenador.html', contexto)
@tipos_permitidos('supervisor')
def supervisor(request):
    return render(request, 'Supervisor.html', contexto_gestao(request))
@tipos_permitidos('coordenador', 'supervisor')
def empresagestao(request):
    # Somente coordenadores podem criar ou editar empresas.
    if request.method == 'POST':
        if request.user.perfil.tipo != 'coordenador':
            messages.error(request, 'Somente o coordenador pode alterar empresas.')
            return redirect('empresagestao')

        acao = request.POST.get('acao', '').strip()
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip().lower()
        senha = request.POST.get('senha', '')

        if acao not in ('cadastrar', 'editar'):
            messages.error(request, 'Operação inválida.')
            return redirect('empresagestao')
        if not nome or len(nome) > 200:
            messages.error(request, 'Informe um nome de empresa válido (até 200 caracteres).')
            return redirect('empresagestao')
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Informe um e-mail válido.')
            return redirect('empresagestao')
        if len(email) > 150:
            messages.error(request, 'O e-mail deve ter até 150 caracteres.')
            return redirect('empresagestao')

        if acao == 'cadastrar':
            if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
                messages.error(request, 'Este e-mail já está cadastrado.')
                return redirect('empresagestao')
            if not senha:
                messages.error(request, 'Informe uma senha para a empresa.')
                return redirect('empresagestao')
            try:
                validate_password(senha)
            except ValidationError as erro:
                messages.error(request, ' '.join(erro.messages))
                return redirect('empresagestao')

            with transaction.atomic():
                usuario = User.objects.create_user(
                    username=email, email=email, password=senha, first_name=nome[:150]
                )
                perfil = Perfil.objects.create(user=usuario, tipo='empresa')
                Empresa.objects.create(perfil=perfil, nome=nome)
            messages.success(request, 'Empresa cadastrada com sucesso!')

        else:
            id_empresa = request.POST.get('id_empresa', '').strip()
            if not id_empresa.isdigit():
                messages.error(request, 'Empresa inválida.')
                return redirect('empresagestao')
            empresa = get_object_or_404(
                Empresa.objects.select_related('perfil__user'), pk=int(id_empresa)
            )
            usuario = empresa.perfil.user
            if User.objects.filter(
                Q(username__iexact=email) | Q(email__iexact=email)
            ).exclude(pk=usuario.pk).exists():
                messages.error(request, 'Este e-mail já pertence a outro usuário.')
                return redirect('empresagestao')
            if senha:
                try:
                    validate_password(senha, user=usuario)
                except ValidationError as erro:
                    messages.error(request, ' '.join(erro.messages))
                    return redirect('empresagestao')

            with transaction.atomic():
                empresa.nome = nome
                empresa.save(update_fields=['nome'])
                usuario.first_name = nome[:150]
                usuario.username = email
                usuario.email = email
                if senha:
                    usuario.set_password(senha)
                usuario.save()
            messages.success(request, 'Empresa atualizada com sucesso!')

        return redirect('empresagestao')

    pesquisa = request.GET.get('q', '').strip()
    hoje = timezone.localdate()
    empresas = Empresa.objects.select_related('perfil__user').annotate(
        total_alunos=Count('alunos', distinct=True),
        total_mentorias=Count('mentorias', distinct=True),
        total_vagas=Count(
            'vaga', filter=Q(vaga__data_limite__gte=hoje), distinct=True
        ),
    ).order_by('nome')
    if pesquisa:
        empresas = empresas.filter(nome__icontains=pesquisa)
    contexto = contexto_gestao(request)
    contexto.update({'empresas': empresas, 'pesquisa': pesquisa})
    return render(request, 'empresagestao.html', contexto)

@tipos_permitidos('coordenador', 'supervisor')
def mentoriasgestao(request):
    from datetime import date
    if request.method == 'POST':
        if request.user.perfil.tipo != 'coordenador':
            messages.error(request, 'Somente o coordenador pode alterar mentorias.')
            return redirect('mentoriasgestao')
        acao = request.POST.get('acao', '').strip()
        tema = request.POST.get('tema', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        data_texto = request.POST.get('data', '').strip()
        horas_texto = request.POST.get('carga_horaria', '').strip()
        if acao not in ('cadastrar', 'editar'):
            messages.error(request, 'Operação inválida.')
            return redirect('mentoriasgestao')
        if not tema or not descricao or not data_texto or not horas_texto:
            messages.error(request, 'Preencha os campos obrigatórios.')
            return redirect('mentoriasgestao')
        try:
            horas = int(horas_texto)
            data_mentoria = date.fromisoformat(data_texto)
            if horas <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, 'Data ou carga horária inválida.')
            return redirect('mentoriasgestao')
        def buscar_relacionado(modelo, campo, rotulo):
            valor = request.POST.get(campo, '').strip()
            if not valor:
                return None
            if not valor.isdigit():
                raise ValueError(f'{rotulo} inválido.')
            objeto = modelo.objects.filter(pk=int(valor)).first()
            if objeto is None:
                raise ValueError(f'{rotulo} não encontrado.')
            return objeto
        try:
            empresa = buscar_relacionado(Empresa, 'empresa', 'Empresa')
            professor = buscar_relacionado(Professor, 'professor', 'Professor')
            supervisor = buscar_relacionado(Supervisor, 'supervisor', 'Supervisor')
        except ValueError as erro:
            messages.error(request, str(erro))
            return redirect('mentoriasgestao')
        if acao == 'editar':
            id_mentoria = request.POST.get('id_mentoria', '').strip()
            if not id_mentoria.isdigit():
                messages.error(request, 'Mentoria inválida.')
                return redirect('mentoriasgestao')
            mentoria = get_object_or_404(Mentoria, pk=int(id_mentoria))
        else:
            mentoria = Mentoria()
        mentoria.tema = tema
        mentoria.descricao = descricao
        mentoria.data = data_mentoria
        mentoria.carga_horaria = horas
        mentoria.empresa = empresa
        mentoria.id_professor = professor
        mentoria.id_supervisor = supervisor
        mentoria.save()
        messages.success(request, 'Mentoria salva com sucesso!')
        return redirect('mentoriasgestao')
    hoje = timezone.localdate()
    pesquisa = request.GET.get('q', '').strip()
    status_selecionado = request.GET.get('status', '').strip()
    empresa_selecionada = request.GET.get('empresa', '').strip()
    consulta = Mentoria.objects.select_related(
        'empresa',
        'id_professor__perfil__user',
        'id_supervisor__perfil__user'
    ).order_by('data')
    if pesquisa:
        consulta = consulta.filter(tema__icontains=pesquisa)
    if empresa_selecionada.isdigit():
        consulta = consulta.filter(empresa_id=int(empresa_selecionada))
    if status_selecionado == 'Em breve':
        consulta = consulta.filter(data__gte=hoje)
    elif status_selecionado == 'Concluída':
        consulta = consulta.filter(data__lt=hoje)
    mentorias = list(consulta)
    participantes = dict(
        Participacao.objects.values('id_mentoria').annotate(
            total=Count('id_aluno')
        ).values_list('id_mentoria', 'total')
    )
    for mentoria in mentorias:
        mentoria.total_alunos = participantes.get(mentoria.pk, 0)
        mentoria.realizada = mentoria.data < hoje
    contexto = contexto_gestao(request)
    contexto.update({
        'mentorias': mentorias,
        'empresas': Empresa.objects.order_by('nome'),
        'professores': Professor.objects.select_related('perfil__user').order_by('perfil__user__first_name'),
        'supervisores': Supervisor.objects.select_related('perfil__user').order_by('perfil__user__first_name'),
        'pesquisa': pesquisa,
        'status_selecionado': status_selecionado,
        'empresa_selecionada': empresa_selecionada,
    })
    return render(request, 'mentoriasgestao.html', contexto)
@tipos_permitidos('coordenador', 'supervisor')
def relatoriosgestao(request):
    hoje = timezone.localdate()
    total_horas = sum(
        resumo_do_aluno(aluno, hoje)[0]
        for aluno in Aluno.objects.all()
    )
    contexto = contexto_gestao(request)
    contexto['total_alunos'] = Aluno.objects.count()
    contexto['total_horas'] = total_horas
    return render(request, 'relatoriosgestao.html', contexto)
@tipos_permitidos('coordenador')
def gerenciaalunosc(request):
    if request.method == 'POST':
        acao = request.POST.get('acao', '').strip()
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip().lower()
        senha = request.POST.get('senha', '')
        curso = request.POST.get('curso', '').strip()
        turma = request.POST.get('turma', '').strip()
        empresa_id = request.POST.get('empresa', '').strip()

        if acao not in ('cadastrar', 'editar'):
            messages.error(request, 'Operação inválida.')
            return redirect('gerenciaalunosc')

        if not nome or not email or not curso or not turma:
            messages.error(request, 'Preencha todos os campos obrigatórios.')
            return redirect('gerenciaalunosc')

        if len(nome) > 150 or len(curso) > 200 or len(turma) > 200:
            messages.error(request, 'Um dos campos ultrapassou o limite de caracteres.')
            return redirect('gerenciaalunosc')

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Informe um e-mail válido.')
            return redirect('gerenciaalunosc')

        if len(email) > 150:
            messages.error(request, 'O e-mail ultrapassou o limite de caracteres.')
            return redirect('gerenciaalunosc')

        empresa = None
        if empresa_id:
            if not empresa_id.isdigit():
                messages.error(request, 'Empresa inválida.')
                return redirect('gerenciaalunosc')
            empresa = Empresa.objects.filter(pk=int(empresa_id)).first()
            if empresa is None:
                messages.error(request, 'Empresa não encontrada.')
                return redirect('gerenciaalunosc')

        if acao == 'cadastrar':
            if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
                messages.error(request, 'Este e-mail já está cadastrado.')
                return redirect('gerenciaalunosc')

            if not senha:
                messages.error(request, 'Informe uma senha para o aluno.')
                return redirect('gerenciaalunosc')

            try:
                validate_password(senha)
            except ValidationError as erro:
                messages.error(request, ' '.join(erro.messages))
                return redirect('gerenciaalunosc')

            with transaction.atomic():
                usuario = User.objects.create_user(
                    username=email, email=email, password=senha, first_name=nome
                )
                perfil = Perfil.objects.create(user=usuario, tipo='aluno')
                Aluno.objects.create(
                    perfil=perfil, curso=curso, turma=turma, empresa=empresa
                )
            messages.success(request, 'Aluno cadastrado com sucesso!')

        elif acao == 'editar':
            id_aluno = request.POST.get('id_aluno', '').strip()
            if not id_aluno.isdigit():
                messages.error(request, 'Aluno inválido.')
                return redirect('gerenciaalunosc')

            aluno = get_object_or_404(
                Aluno.objects.select_related('perfil__user'), pk=int(id_aluno)
            )
            usuario = aluno.perfil.user
            if User.objects.filter(
                Q(username__iexact=email) | Q(email__iexact=email)
            ).exclude(pk=usuario.pk).exists():
                messages.error(request, 'Este e-mail já pertence a outro usuário.')
                return redirect('gerenciaalunosc')

            if senha:
                try:
                    validate_password(senha, user=usuario)
                except ValidationError as erro:
                    messages.error(request, ' '.join(erro.messages))
                    return redirect('gerenciaalunosc')

            with transaction.atomic():
                usuario.first_name = nome
                usuario.email = email
                usuario.username = email
                if senha:
                    usuario.set_password(senha)
                usuario.save()
                aluno.curso = curso
                aluno.turma = turma
                aluno.empresa = empresa
                aluno.save()
            messages.success(request, 'Aluno atualizado com sucesso!')

        return redirect('gerenciaalunosc')

    hoje = timezone.localdate()
    pesquisa = request.GET.get('q', '').strip()
    status_selecionado = request.GET.get('status', '').strip()

    # Indicadores mostram os totais gerais, independentemente da pesquisa.
    consulta = Aluno.objects.select_related('perfil__user', 'empresa').order_by(
        'perfil__user__first_name'
    )
    todos = []
    for aluno in consulta:
        horas, tem_atraso = resumo_do_aluno(aluno, hoje)
        usuario = aluno.perfil.user
        status = 'Pendente' if tem_atraso else ('Em estágio' if aluno.empresa_id else 'Ativo')
        todos.append({
            'id': aluno.pk,
            'nome': usuario.get_full_name() or usuario.username,
            'email': usuario.email,
            'curso': aluno.curso,
            'turma': aluno.turma,
            'empresa': aluno.empresa.nome if aluno.empresa else None,
            'empresa_id': aluno.empresa_id or '',
            'horas': horas,
            'status': status,
        })

    alunos = [a for a in todos if (
        (not pesquisa or pesquisa.lower() in a['nome'].lower() or pesquisa.lower() in a['email'].lower())
        and (not status_selecionado or a['status'] == status_selecionado)
    )]

    contexto = contexto_gestao(request)
    contexto.update({
        'alunos': alunos,
        'empresas': Empresa.objects.order_by('nome'),
        'pesquisa': pesquisa,
        'status_selecionado': status_selecionado,
        'total_alunos': len(todos),
        'alunos_ativos': sum(a['status'] == 'Ativo' for a in todos),
        'alunos_estagio': sum(a['status'] == 'Em estágio' for a in todos),
        'alunos_pendentes': sum(a['status'] == 'Pendente' for a in todos),
    })
    return render(request, 'gerenciaalunosc.html', contexto)


# ---------------------------------------------------------------------
# LOGIN / LOGOUT
# ---------------------------------------------------------------------
# Cada tela de login: (página HTML, tipo de usuário que pode entrar nela)
TELAS_DE_LOGIN = {
    'login': ('loginAluno.html', 'aluno'),
    'login_aluno': ('loginAluno.html', 'aluno'),
    'login_professor': ('loginProfessor.html', 'professor'),
    'login_coordenador': ('loginCoordenador.html', 'coordenador'),
    'login_supervisor': ('loginSupervisor.html', 'supervisor'),
    'login_empresa': ('loginempresa.html', 'empresa'),
}
def login_view(request):
    nome_da_rota = request.resolver_match.url_name
    pagina, tipo_da_tela = TELAS_DE_LOGIN.get(
        nome_da_rota,
        ('loginAluno.html', 'aluno')
    )
    if request.method == 'POST':
        email = (
            request.POST.get('email')
            or request.POST.get('username')
            or ''
        ).strip().lower()
        senha = request.POST.get('senha')
        usuario = authenticate(
            request,
            username=email,
            password=senha
        )
        if usuario is not None:
            if not hasattr(usuario, 'perfil'):
                return render(
                    request,
                    pagina,
                    {
                        'erro': 'Este usuário não possui um perfil cadastrado.',
                        'email': email
                    }
                )
            if usuario.perfil.tipo != tipo_da_tela:
                return render(
                    request,
                    pagina,
                    {
                        'erro': f'Este e-mail não está cadastrado como {tipo_da_tela}.',
                        'email': email
                    }
                )
            login(request, usuario)
            return redirecionar_por_tipo(usuario.perfil.tipo)
        return render(
            request,
            pagina,
            {
                'erro': 'E-mail ou senha inválidos.',
                'email': email
            }
        )
    return render(request, pagina)
def logout_view(request):
    logout(request)
    return redirect('login')
# ---------------------------------------------------------------------
# ÁREA DO ALUNO
# ---------------------------------------------------------------------
@tipo_permitido('aluno')
def minhasmentoriasa(request):
    aluno = obter_aluno(request)
    participacoes = Participacao.objects.filter(
        id_aluno=aluno
    ).select_related(
        'id_mentoria',
        'id_mentoria__id_professor__perfil__user',
        'id_mentoria__id_supervisor__perfil__user'
    ).order_by('id_mentoria__data')
    hoje = timezone.localdate()
    proximas = [
        p for p in participacoes
        if p.id_mentoria.data >= hoje
    ]
    realizadas = [
        p for p in participacoes
        if p.id_mentoria.data < hoje
    ]
    realizadas.reverse()
    return render(
        request,
        'aluno/minhasmentoriasa.html',
        {
            'aluno': aluno,
            'proximas': proximas,
            'realizadas': realizadas,
            'nome_usuario': nome_do_usuario(request)
        }
    )
@tipo_permitido('aluno')
def detalhesdamentoriaa(request, id_mentoria):
    aluno = obter_aluno(request)
    participacao = get_object_or_404(
        Participacao.objects.select_related(
            'id_mentoria__id_professor__perfil__user',
            'id_mentoria__id_supervisor__perfil__user'
        ),
        id_aluno=aluno,
        id_mentoria_id=id_mentoria
    )
    mentoria = participacao.id_mentoria
    hoje = timezone.localdate()
    atividades = list(
        mentoria.atividades.all().order_by('data_entrega', 'id_atividade')
    )
    for atividade in atividades:
        atividade.situacao, atividade.situacao_texto = situacao_atividade(
            atividade,
            hoje
        )
    return render(
        request,
        'aluno/detalhesdamentoriaa.html',
        {
            'aluno': aluno,
            'mentoria': mentoria,
            'participacao': participacao,
            'atividades': atividades,
            'realizada': mentoria.data < hoje,
            'nome_usuario': nome_do_usuario(request)
        }
    )
@tipo_permitido('aluno')
def meuperfila(request):
    aluno = obter_aluno(request)
    return render(
        request,
        'aluno/meuperfila.html',
        {
            'aluno': aluno,
            'usuario': request.user,
            'nome_usuario': nome_do_usuario(request)
        }
    )
@tipo_permitido('aluno')
def meusportifoliosa(request):
    aluno = obter_aluno(request)
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
            'nome_usuario': nome_do_usuario(request)
        }
    )
@tipo_permitido('aluno')
def atividadesa(request):
    aluno = obter_aluno(request)
    hoje = timezone.localdate()
    pendentes, concluidas, atrasadas = classificar_atividades(
        atividades_do_aluno(aluno),
        hoje
    )
    return render(
        request,
        'aluno/atividadesa.html',
        {
            'aluno': aluno,
            'pendentes': pendentes,
            'concluidas': concluidas,
            'atrasadas': atrasadas,
            'nome_usuario': nome_do_usuario(request)
        }
    )
@tipo_permitido('aluno')
def detalhesdaatividadea(request, id_atividade):
    aluno = obter_aluno(request)
    atividade = get_object_or_404(
        atividades_do_aluno(aluno),
        id_atividade=id_atividade
    )
    situacao, situacao_texto = situacao_atividade(
        atividade,
        timezone.localdate()
    )
    return render(
        request,
        'aluno/detalhesdaatividadea.html',
        {
            'aluno': aluno,
            'atividade': atividade,
            'mentoria': atividade.id_mentoria,
            'situacao': situacao,
            'situacao_texto': situacao_texto,
            'nome_usuario': nome_do_usuario(request)
        }
    )
@tipo_permitido('aluno')
def pendenciasa(request):
    aluno = obter_aluno(request)
    em_atraso, proximas, outras = montar_pendencias(
        aluno,
        timezone.localdate()
    )
    return render(
        request,
        'aluno/pendenciasa.html',
        {
            'aluno': aluno,
            'em_atraso': em_atraso,
            'proximas': proximas,
            'outras': outras,
            'total_pendencias': len(em_atraso) + len(proximas) + len(outras),
            'nome_usuario': nome_do_usuario(request)
        }
    )
@tipo_permitido('aluno')
def certificadoa(request):
    aluno = obter_aluno(request)
    if request.method == 'POST':
        curso = request.POST.get('curso', '').strip()[:200]
        instituicao = request.POST.get('instituicao', '').strip()[:200]
        carga_horaria = request.POST.get('carga_horaria', '').strip()
        if (
            not curso
            or not instituicao
            or not carga_horaria.isdigit()
            or int(carga_horaria) < 1
        ):
            messages.error(
                request,
                'Preencha todos os campos corretamente.'
            )
        else:
            Certificado.objects.create(
                id_aluno=aluno,
                curso=curso,
                instituicao=instituicao,
                carga_horaria=int(carga_horaria),
                status='Em análise'
            )
            messages.success(
                request,
                'Certificado enviado para análise.'
            )
        return redirect('certificadoa')
    certificados = list(
        Certificado.objects.filter(
            id_aluno=aluno
        ).order_by('-id_certificado')
    )
    for certificado in certificados:
        certificado.classe = classe_certificado(certificado.status)
    return render(
        request,
        'aluno/certificadoa.html',
        {
            'aluno': aluno,
            'certificados': certificados,
            'total_aprovados': sum(
                1 for c in certificados if c.classe == 'aprovado'
            ),
            'total_analise': sum(
                1 for c in certificados if c.classe == 'analise'
            ),
            'total_pendentes': sum(
                1 for c in certificados if c.classe == 'pendente'
            ),
            'nome_usuario': nome_do_usuario(request)
        }
    )
# ---------------------------------------------------------------------
# CADASTRO
# ---------------------------------------------------------------------
def cadastro(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip().lower()
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
        messages.success(
            request,
            'Cadastro realizado! Escolha seu tipo de acesso para entrar.'
        )
        return redirect('index')
    return render(request, 'cadastro.html')
# ---------------------------------------------------------------------
# PROFESSOR
# ---------------------------------------------------------------------
@tipo_permitido('professor')
def portfoliosp(request):
    return render(request, 'professor/portfoliosp.html')
@tipo_permitido('professor')
def avaliacoesp(request):
    return render(request, 'professor/avaliacoesp.html')
@tipo_permitido('professor')
def mentoriasp(request):
    return render(request, 'professor/mentoriasp.html')
@tipo_permitido('professor')
def agendap(request):
    return render(request, 'professor/agendap.html')
# ---------------------------------------------------------------------
# EMPRESA
# ---------------------------------------------------------------------
@tipo_permitido('empresa')
def cadastrarmentoriase(request):
    return render(request, 'empresa/cadastrarmentoriase.html')
@tipo_permitido('empresa')
def criartarefase(request):
    return render(request, 'empresa/criartarefase.html')
@tipo_permitido('empresa')
def oportunidadese(request):
    return render(request, 'empresa/oportunidadese.html')