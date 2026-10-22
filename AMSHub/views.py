from PIL import Image, UnidentifiedImageError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, URLValidator
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from django.utils import timezone
from functools import wraps
import datetime
from decimal import Decimal, InvalidOperation
import re
from .models import (
    Perfil,
    Aluno,
    Professor,
    Supervisor,
    Empresa,
    Mentoria,
    Participacao,
    Portfolio,
    EntregaPortfolio,
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

FORMATOS_FOTO = ('JPEG', 'PNG', 'WEBP')
TAMANHO_MAX_FOTO = 2 * 1024 * 1024  # 2 MB


def validar_foto(arquivo):
    """Devolve uma mensagem de erro, ou None se a foto for válida."""
    if not arquivo:
        return 'Selecione uma imagem.'
    if arquivo.size > TAMANHO_MAX_FOTO:
        return 'A foto deve ter no máximo 2 MB.'
    try:
        imagem = Image.open(arquivo)
        formato = imagem.format
        imagem.verify()
    except (UnidentifiedImageError, OSError):
        return 'O arquivo enviado não é uma imagem válida.'
    finally:
        arquivo.seek(0)
    if formato not in FORMATOS_FOTO:
        return 'Use uma imagem JPG, PNG ou WEBP.'
    return None

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
# ---------------------------------------------------------------------
# PROFESSOR (funções auxiliares)
# ---------------------------------------------------------------------

STATUS_ENTREGA_PENDENTE = 'Pendente'
STATUS_ENTREGA_AVALIADA = 'Avaliado'


def obter_professor(request):
    """Professor do usuário logado (cada professor só vê o que é dele)."""
    return get_object_or_404(
        Professor,
        perfil__user=request.user
    )


def entregas_do_professor(professor_logado):
    """Entregas de portfólio das mentorias em que ele é o professor."""
    return EntregaPortfolio.objects.filter(
        id_mentoria__id_professor=professor_logado
    ).select_related(
        'id_aluno__perfil__user',
        'id_mentoria'
    )


def nome_do_aluno(aluno):
    usuario = aluno.perfil.user
    return usuario.get_full_name() or usuario.username


def ler_nota(texto):
    """Lê uma nota de 0 a 10 (aceita vírgula). Devolve Decimal ou None."""
    try:
        valor = Decimal((texto or '').strip().replace(',', '.'))
    except InvalidOperation:
        return None
    if not valor.is_finite() or valor < 0 or valor > 10:
        return None
    return valor.quantize(Decimal('0.1'))


@tipo_permitido('professor')
def professor(request):

    professor_logado = obter_professor(request)
    hoje = timezone.localdate()

    # Todas as mentorias aparecem para todos os professores.
    mentorias = Mentoria.objects.all()
    entregas = entregas_do_professor(professor_logado)

    pendentes = entregas.filter(status=STATUS_ENTREGA_PENDENTE)
    avaliadas = entregas.filter(status=STATUS_ENTREGA_AVALIADA)

    contexto = {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'total_pendentes': pendentes.count(),
        'total_avaliacoes': avaliadas.count(),
        'feedbacks_mes': avaliadas.filter(
            data_avaliacao__year=hoje.year,
            data_avaliacao__month=hoje.month
        ).exclude(feedback='').count(),
        'mentorias_agendadas': mentorias.filter(data__gte=hoje).count(),
        'portfolios_recentes': pendentes.order_by('-data_envio')[:3],
        'proximas_mentorias': mentorias.filter(
            data__gte=hoje
        ).order_by('data', 'horario')[:3],
    }

    return render(request, 'Professor.html', contexto)
def obter_empresa(request):
    """Empresa do usuário logado (cada empresa só mexe no que é dela)."""
    return get_object_or_404(
        Empresa,
        perfil__user=request.user
    )
@tipo_permitido('empresa')
def empresa(request):
    empresa_logada = obter_empresa(request)
    hoje = timezone.localdate()
    mentorias = Mentoria.objects.filter(empresa=empresa_logada)
    atividades = Atividade.objects.filter(id_mentoria__empresa=empresa_logada)
    vagas = Vaga.objects.filter(id_empresa=empresa_logada)
    vagas_publicadas = list(vagas.order_by('-id_vaga')[:5])
    for vaga in vagas_publicadas:
        vaga.aberta = vaga.data_limite >= hoje
    tarefas_recentes = list(
        atividades.select_related('id_mentoria').order_by('-id_atividade')[:4]
    )
    for tarefa in tarefas_recentes:
        tarefa.concluida = atividade_concluida(tarefa)
    contexto = {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'total_mentorias_ativas': mentorias.filter(data__gte=hoje).count(),
        'total_tarefas': atividades.count(),
        'total_vagas_abertas': vagas.filter(data_limite__gte=hoje).count(),
        'vagas_publicadas': vagas_publicadas,
        'mentorias_recentes': mentorias.order_by('-id_mentoria')[:3],
        'tarefas_recentes': tarefas_recentes,
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
    perfil = request.user.perfil

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'enviar_foto':
            arquivo = request.FILES.get('foto')
            erro = validar_foto(arquivo)
            if erro:
                messages.error(request, erro)
            else:
                if perfil.foto:
                    perfil.foto.delete(save=False)  # apaga a foto antiga
                perfil.foto = arquivo
                perfil.save(update_fields=['foto'])
                messages.success(request, 'Foto atualizada com sucesso!')

        elif acao == 'remover_foto':
            if perfil.foto:
                perfil.foto.delete(save=True)
            messages.success(request, 'Foto removida.')

        else:
            messages.error(request, 'Operação inválida.')

        return redirect('meuperfila')

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

    if request.method == 'POST':
        if request.POST.get('acao') != 'adicionar_entrega':
            messages.error(request, 'Operação inválida.')
            return redirect('meusportifoliosa')

        titulo = request.POST.get('titulo', '').strip()
        ano_texto = request.POST.get('ano', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        tipo_envio = request.POST.get('tipo_envio', '').strip()
        mentoria_id = request.POST.get('mentoria', '').strip()
        link = request.POST.get('link', '').strip()
        arquivo = request.FILES.get('arquivo')

        if not titulo or len(titulo) > 200 or ano_texto not in ('1', '2', '3'):
            messages.error(request, 'Informe o título e o ano corretamente.')
            return redirect('meusportifoliosa')

        mentoria = None
        if mentoria_id:
            if not mentoria_id.isdigit():
                messages.error(request, 'Mentoria inválida.')
                return redirect('meusportifoliosa')
            mentoria = Mentoria.objects.filter(
                pk=int(mentoria_id),
                participacao__id_aluno=aluno
            ).distinct().first()
            if mentoria is None:
                messages.error(request, 'Você não está inscrito nessa mentoria.')
                return redirect('meusportifoliosa')

        if tipo_envio == 'link':
            if not link or len(link) > 1000:
                messages.error(request, 'Informe um link válido.')
                return redirect('meusportifoliosa')
            try:
                URLValidator(schemes=['http', 'https'])(link)
            except ValidationError:
                messages.error(request, 'Informe um link HTTP ou HTTPS válido.')
                return redirect('meusportifoliosa')
            arquivo = None
        elif tipo_envio == 'pdf':
            link = ''
            if not arquivo:
                messages.error(request, 'Selecione um PDF para enviar.')
                return redirect('meusportifoliosa')
            if not arquivo.name.lower().endswith('.pdf') or arquivo.size > 10 * 1024 * 1024:
                messages.error(request, 'O arquivo deve ser PDF e ter no máximo 10 MB.')
                return redirect('meusportifoliosa')
            if arquivo.read(5) != b'%PDF-':
                messages.error(request, 'O arquivo enviado não parece ser um PDF válido.')
                return redirect('meusportifoliosa')
            arquivo.seek(0)
        else:
            messages.error(request, 'Escolha enviar um link ou PDF.')
            return redirect('meusportifoliosa')

        EntregaPortfolio.objects.create(
            id_aluno=aluno,
            id_mentoria=mentoria,
            titulo=titulo,
            ano=int(ano_texto),
            descricao=descricao,
            link=link,
            arquivo=arquivo
        )
        messages.success(request, 'Entrega adicionada ao portfólio com sucesso!')
        return redirect('meusportifoliosa')

    portfolios = Portfolio.objects.filter(
        id_aluno=aluno
    ).select_related('id_mentoria')
    entregas = EntregaPortfolio.objects.filter(
        id_aluno=aluno
    ).select_related('id_mentoria')
    mentorias = Mentoria.objects.filter(
        participacao__id_aluno=aluno
    ).distinct().order_by('tema')

    return render(request, 'aluno/meusportifoliosa.html', {
        'aluno': aluno,
        'portfolios': portfolios,
        'entregas': entregas,
        'mentorias': mentorias,
        'nome_usuario': nome_do_usuario(request)
    })

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

    professor_logado = obter_professor(request)
    entregas_base = entregas_do_professor(professor_logado)

    # Salvar a avaliação (nota + feedback) de uma entrega
    if request.method == 'POST':

        id_entrega = request.POST.get('id_entrega', '').strip()
        nota = ler_nota(request.POST.get('nota', ''))
        feedback = request.POST.get('feedback', '').strip()

        if not id_entrega.isdigit():
            messages.error(request, 'Entrega inválida.')

        elif nota is None:
            messages.error(request, 'Informe uma nota de 0 a 10.')

        elif len(feedback) > 2000:
            messages.error(request, 'O feedback deve ter até 2000 caracteres.')

        else:
            # Só dá para avaliar entrega de mentoria do próprio professor.
            entrega = entregas_base.filter(pk=int(id_entrega)).first()

            if entrega is None:
                messages.error(request, 'Entrega não encontrada.')
            else:
                entrega.nota = nota
                entrega.feedback = feedback
                entrega.status = STATUS_ENTREGA_AVALIADA
                entrega.data_avaliacao = timezone.now()
                entrega.avaliador = professor_logado
                entrega.save(update_fields=[
                    'nota', 'feedback', 'status',
                    'data_avaliacao', 'avaliador'
                ])
                messages.success(request, 'Avaliação salva com sucesso!')

        return redirect('portfoliosp')

    pesquisa = request.GET.get('q', '').strip()
    filtro = request.GET.get('status', '').strip()
    avaliar = request.GET.get('avaliar', '').strip()

    consulta = entregas_base.order_by('-data_envio')

    if pesquisa:
        consulta = consulta.filter(
            Q(titulo__icontains=pesquisa)
            | Q(id_aluno__perfil__user__first_name__icontains=pesquisa)
            | Q(id_mentoria__tema__icontains=pesquisa)
        )

    if filtro in (STATUS_ENTREGA_PENDENTE, STATUS_ENTREGA_AVALIADA):
        consulta = consulta.filter(status=filtro)
    else:
        filtro = ''

    # Pendentes primeiro (a ordenação do Python é estável: mantém a data)
    portfolios = sorted(
        consulta,
        key=lambda entrega: entrega.status != STATUS_ENTREGA_PENDENTE
    )

    for entrega in portfolios:
        entrega.aluno_nome = nome_do_aluno(entrega.id_aluno)

    return render(request, 'professor/portfoliosp.html', {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'portfolios': portfolios,
        'pesquisa': pesquisa,
        'filtro': filtro,
        'avaliar_id': int(avaliar) if avaliar.isdigit() else '',
        'total_pendentes': entregas_base.filter(
            status=STATUS_ENTREGA_PENDENTE
        ).count(),
    })


@tipo_permitido('professor')
def avaliacoesp(request):

    professor_logado = obter_professor(request)
    entregas = entregas_do_professor(professor_logado)

    avaliadas = entregas.filter(
        status=STATUS_ENTREGA_AVALIADA
    ).order_by('-data_avaliacao', '-data_envio')

    avaliacoes = [
        {
            'id': entrega.pk,
            'aluno': nome_do_aluno(entrega.id_aluno),
            'atividade': entrega.titulo,
            'nota': entrega.nota,
            'feedback': entrega.feedback,
            'data': entrega.data_avaliacao,
        }
        for entrega in avaliadas
    ]

    return render(request, 'professor/avaliacoesp.html', {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'avaliacoes': avaliacoes,
        'total_avaliacoes': len(avaliacoes),
        'avaliacoes_pendentes': entregas.filter(
            status=STATUS_ENTREGA_PENDENTE
        ).count(),
    })


@tipo_permitido('professor')
def mentoriasp(request):

    professor_logado = obter_professor(request)
    hoje = timezone.localdate()

    # Todas as mentorias aparecem para todos os professores.
    todas = list(
        Mentoria.objects.select_related(
            'empresa',
            'id_professor__perfil__user'
        ).annotate(
            inscritos=Count('participacao', distinct=True)
        )
    )

    for mentoria in todas:
        mentoria.minha = mentoria.id_professor_id == professor_logado.pk
        mentoria.realizada = mentoria.data < hoje
        mentoria.carga_texto = formatar_horas(mentoria.carga_horaria)

    # Próximas primeiro (da mais perto para a mais longe), depois as realizadas
    proximas = sorted(
        (m for m in todas if not m.realizada),
        key=lambda m: (m.data, m.horario or datetime.time.max)
    )
    realizadas = sorted(
        (m for m in todas if m.realizada),
        key=lambda m: m.data,
        reverse=True
    )

    return render(request, 'professor/mentoriasp.html', {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'mentorias': proximas + realizadas,
    })


@tipo_permitido('professor')
def agendap(request):

    obter_professor(request)
    hoje = timezone.localdate()

    eventos = []

    # Mentorias que ainda vão acontecer
    mentorias = Mentoria.objects.filter(
        data__gte=hoje
    ).select_related('empresa')

    for mentoria in mentorias:

        horario = ''

        if mentoria.horario:
            horario = mentoria.horario.strftime('%H:%M')

            fim = datetime.datetime.combine(
                mentoria.data,
                mentoria.horario
            ) + datetime.timedelta(hours=float(mentoria.carga_horaria))

            if fim.date() == mentoria.data:
                horario += ' às ' + fim.strftime('%H:%M')

        partes = [
            mentoria.empresa.nome if mentoria.empresa else '',
            mentoria.modalidade,
        ]

        eventos.append({
            'data': mentoria.data,
            'ordem': mentoria.horario or datetime.time.max,
            'titulo': mentoria.tema,
            'descricao': ' · '.join(p for p in partes if p),
            'horario': horario,
            'tipo': 'Mentoria',
        })

    # Prazos das atividades dessas mentorias que ainda estão abertas
    atividades = Atividade.objects.filter(
        data_entrega__gte=hoje
    ).select_related('id_mentoria')

    for atividade in atividades:

        if atividade_concluida(atividade):
            continue

        eventos.append({
            'data': atividade.data_entrega,
            'ordem': datetime.time.max,
            'titulo': atividade.titulo,
            'descricao': f'Prazo de entrega · {atividade.id_mentoria.tema}',
            'horario': 'Dia todo',
            'tipo': 'Prazo',
        })

    eventos.sort(key=lambda evento: (evento['data'], evento['ordem']))

    return render(request, 'professor/agendap.html', {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'eventos': eventos[:50],
    })
# ---------------------------------------------------------------------
# EMPRESA
# ---------------------------------------------------------------------
MODALIDADES_MENTORIA = ('Online', 'Presencial', 'Híbrida')
PRIORIDADES_TAREFA = ('Baixa', 'Média', 'Alta')
TIPOS_VAGA = ('Estágio', 'Emprego', 'Jovem Aprendiz')
MODALIDADES_VAGA = ('Presencial', 'Remoto', 'Híbrido')
def ler_data(texto):
    """Converte 'AAAA-MM-DD' em data; devolve None se for inválida."""
    try:
        return datetime.date.fromisoformat(texto)
    except ValueError:
        return None
def ler_horas(texto):
    """Lê horas como '2', '1,5', '1.5', '1h30', '2h' ou '1h30m'.
    Devolve Decimal (ex.: 1h30 -> 1.5) ou None se for inválido."""
    texto = texto.strip().lower().replace(' ', '')
    achou = re.fullmatch(r'(\d{1,3})h(?:(\d{1,2})m?)?', texto)
    if achou:
        minutos = int(achou.group(2) or 0)
        if minutos > 59:
            return None
        return (Decimal(achou.group(1)) + Decimal(minutos) / 60).quantize(Decimal('0.01'))
    try:
        valor = Decimal(texto.replace(',', '.'))
    except InvalidOperation:
        return None
    if not valor.is_finite() or valor < 0 or valor > 999:
        return None
    return valor.quantize(Decimal('0.01'))
def formatar_horas(valor):
    """1.5 -> '1h30', 2 -> '2h', 0.5 -> '30min'."""
    minutos = int((Decimal(valor) * 60).quantize(Decimal('1')))
    horas, resto = divmod(minutos, 60)
    if horas and resto:
        return f'{horas}h{resto:02d}'
    if horas:
        return f'{horas}h'
    return f'{resto}min'
def ler_horario(texto):
    """Converte 'HH:MM' em horário; devolve None se for inválido."""
    try:
        return datetime.time.fromisoformat(texto)
    except ValueError:
        return None
def id_para_editar(request):
    """Lê o ?editar=ID da URL (ou o campo escondido 'id' do formulário)."""
    valor = request.POST.get('id', '') if request.method == 'POST' else request.GET.get('editar', '')
    valor = valor.strip()
    return int(valor) if valor.isdecimal() else None
@tipo_permitido('empresa')
def cadastrarmentoriase(request):
    empresa_logada = obter_empresa(request)
    hoje = timezone.localdate()
    minhas = Mentoria.objects.filter(empresa=empresa_logada)
    editando = None
    editar_id = id_para_editar(request)
    if editar_id is not None:
        # Só dá para editar mentoria da própria empresa.
        editando = minhas.filter(pk=editar_id).first()
        if editando is None:
            messages.error(request, 'Mentoria não encontrada.')
            return redirect('cadastrarmentoriase')
    form = {}
    if request.method == 'POST':
        form = request.POST
        titulo = form.get('titulo', '').strip()
        area = form.get('area', '').strip()
        data_mentoria = ler_data(form.get('data', '').strip())
        horario = ler_horario(form.get('horario', '').strip())
        vagas = form.get('vagas', '').strip()
        carga_horaria = ler_horas(form.get('carga_horaria', ''))
        modalidade = form.get('modalidade', '').strip()
        descricao = form.get('descricao', '').strip()
        erro = None
        if not titulo or len(titulo) > 200:
            erro = 'Informe um título de até 200 caracteres.'
        elif not area or len(area) > 100:
            erro = 'Informe a área de conhecimento (até 100 caracteres).'
        elif data_mentoria is None or horario is None:
            erro = 'Informe uma data e um horário válidos.'
        elif data_mentoria < hoje and not (editando and editando.data == data_mentoria):
            erro = 'A data da mentoria não pode estar no passado.'
        elif vagas and (not vagas.isdecimal() or int(vagas) > 9999):
            erro = 'Informe as vagas de 0 a 9999 (0 ou vazio = sem limite).'
        elif carga_horaria is None or carga_horaria <= 0:
            erro = 'Informe a carga horária, por exemplo 2, 1,5 ou 1h30.'
        elif modalidade not in MODALIDADES_MENTORIA:
            erro = 'Escolha uma modalidade válida.'
        elif not descricao:
            erro = 'Descreva a mentoria.'
        if erro is None:
            mentoria = editando or Mentoria(empresa=empresa_logada)
            mentoria.tema = titulo
            mentoria.descricao = descricao
            mentoria.data = data_mentoria
            mentoria.carga_horaria = carga_horaria
            mentoria.area = area
            mentoria.horario = horario
            mentoria.vagas = int(vagas or 0)
            mentoria.modalidade = modalidade
            mentoria.save()
            messages.success(
                request,
                'Mentoria atualizada com sucesso!' if editando else 'Mentoria cadastrada com sucesso!'
            )
            return redirect('cadastrarmentoriase')
        messages.error(request, erro)
    elif editando:
        form = {
            'titulo': editando.tema,
            'area': editando.area,
            'data': editando.data.isoformat(),
            'horario': editando.horario.strftime('%H:%M') if editando.horario else '',
            'vagas': editando.vagas if editando.vagas is not None else '',
            'carga_horaria': formatar_horas(editando.carga_horaria),
            'modalidade': editando.modalidade,
            'descricao': editando.descricao,
        }
    mentorias = list(minhas.annotate(
        inscritos=Count('participacao', distinct=True)
    ).order_by('-data', '-id_mentoria'))
    for mentoria in mentorias:
        mentoria.carga_texto = formatar_horas(mentoria.carga_horaria)
    return render(request, 'empresa/cadastrarmentoriase.html', {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'mentorias': mentorias,
        'form': form,
        'editando': editando,
    })
@tipo_permitido('empresa')
def criartarefase(request):
    empresa_logada = obter_empresa(request)
    hoje = timezone.localdate()
    mentorias = Mentoria.objects.filter(
        empresa=empresa_logada
    ).order_by('-data', '-id_mentoria')
    minhas = Atividade.objects.filter(id_mentoria__empresa=empresa_logada)
    editando = None
    editar_id = id_para_editar(request)
    if editar_id is not None:
        editando = minhas.filter(pk=editar_id).first()
        if editando is None:
            messages.error(request, 'Tarefa não encontrada.')
            return redirect('criartarefase')
    form = {}
    if request.method == 'POST':
        form = request.POST
        mentoria_id = form.get('mentoria', '').strip()
        titulo = form.get('titulo', '').strip()
        prazo = ler_data(form.get('prazo', '').strip())
        prioridade = form.get('prioridade', '').strip()
        horas = ler_horas(form.get('horas', '') or '0')
        descricao = form.get('descricao', '').strip()
        # Só vale uma mentoria que pertença à empresa logada.
        mentoria = None
        if mentoria_id.isdecimal():
            mentoria = mentorias.filter(pk=int(mentoria_id)).first()
        erro = None
        if mentoria is None:
            erro = 'Escolha uma das mentorias da sua empresa.'
        elif not titulo or len(titulo) > 200:
            erro = 'Informe um título de até 200 caracteres.'
        elif prazo is None:
            erro = 'Informe um prazo de entrega válido.'
        elif prazo < hoje and not (editando and editando.data_entrega == prazo):
            erro = 'O prazo de entrega não pode estar no passado.'
        elif prioridade not in PRIORIDADES_TAREFA:
            erro = 'Escolha uma prioridade válida.'
        elif horas is None:
            erro = 'Informe as horas, por exemplo 2, 1,5 ou 1h30.'
        elif not descricao:
            erro = 'Explique o que o aluno deverá desenvolver.'
        if erro is None:
            tarefa = editando or Atividade(status='Pendente')
            tarefa.id_mentoria = mentoria
            tarefa.titulo = titulo
            tarefa.descricao = descricao
            tarefa.data_entrega = prazo
            tarefa.horas = horas
            tarefa.prioridade = prioridade
            tarefa.save()
            messages.success(
                request,
                'Tarefa atualizada com sucesso!' if editando else 'Tarefa criada com sucesso!'
            )
            return redirect('criartarefase')
        messages.error(request, erro)
    elif editando:
        form = {
            'mentoria': str(editando.id_mentoria_id),
            'titulo': editando.titulo,
            'prazo': editando.data_entrega.isoformat() if editando.data_entrega else '',
            'prioridade': editando.prioridade,
            'horas': formatar_horas(editando.horas),
            'descricao': editando.descricao,
        }
    tarefas = list(
        minhas.select_related('id_mentoria').order_by('-id_atividade')
    )
    for tarefa in tarefas:
        tarefa.situacao, tarefa.situacao_texto = situacao_atividade(
            tarefa,
            hoje
        )
    return render(request, 'empresa/criartarefase.html', {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'mentorias': mentorias,
        'tarefas': tarefas,
        'form': form,
        'editando': editando,
    })
@tipo_permitido('empresa')
def oportunidadese(request):
    empresa_logada = obter_empresa(request)
    hoje = timezone.localdate()
    minhas = Vaga.objects.filter(id_empresa=empresa_logada)
    editando = None
    editar_id = id_para_editar(request)
    if editar_id is not None:
        editando = minhas.filter(pk=editar_id).first()
        if editando is None:
            messages.error(request, 'Oportunidade não encontrada.')
            return redirect('oportunidadese')
    form = {}
    if request.method == 'POST':
        form = request.POST
        titulo = form.get('titulo', '').strip()
        tipo = form.get('tipo', '').strip()
        modalidade = form.get('modalidade', '').strip()
        localizacao = form.get('localizacao', '').strip()
        prazo = ler_data(form.get('prazo', '').strip())
        quantidade = form.get('vagas', '').strip()
        descricao = form.get('descricao', '').strip()
        requisitos = form.get('requisitos', '').strip()
        erro = None
        if not titulo or len(titulo) > 200:
            erro = 'Informe um título de até 200 caracteres.'
        elif tipo not in TIPOS_VAGA:
            erro = 'Escolha o tipo de oportunidade.'
        elif modalidade not in MODALIDADES_VAGA:
            erro = 'Escolha uma modalidade válida.'
        elif len(localizacao) > 150:
            erro = 'A localização pode ter até 150 caracteres.'
        elif prazo is None:
            erro = 'Informe o prazo para inscrição.'
        elif prazo < hoje and not (editando and editando.data_limite == prazo):
            erro = 'O prazo para inscrição não pode estar no passado.'
        elif quantidade and (not quantidade.isdecimal() or int(quantidade) > 9999):
            erro = 'Informe as vagas de 0 a 9999 (0 ou vazio = sem limite).'
        elif not descricao:
            erro = 'Descreva a oportunidade.'
        elif len(requisitos) > 500:
            erro = 'Os requisitos podem ter até 500 caracteres.'
        if erro is None:
            vaga = editando or Vaga(id_empresa=empresa_logada)
            vaga.cargo = titulo
            vaga.descricao = descricao
            vaga.requisitos = requisitos
            vaga.data_limite = prazo
            vaga.tipo = tipo
            vaga.modalidade = modalidade
            vaga.localizacao = localizacao
            vaga.quantidade = int(quantidade) if quantidade else 0
            vaga.save()
            messages.success(
                request,
                'Oportunidade atualizada com sucesso!' if editando else 'Oportunidade publicada com sucesso!'
            )
            return redirect('oportunidadese')
        messages.error(request, erro)
    elif editando:
        form = {
            'titulo': editando.cargo,
            'tipo': editando.tipo,
            'modalidade': editando.modalidade,
            'localizacao': editando.localizacao,
            'prazo': editando.data_limite.isoformat(),
            'vagas': editando.quantidade if editando.quantidade is not None else '',
            'descricao': editando.descricao,
            'requisitos': editando.requisitos,
        }
    oportunidades = list(minhas.order_by('-id_vaga'))
    for oportunidade in oportunidades:
        oportunidade.aberta = oportunidade.data_limite >= hoje
    return render(request, 'empresa/oportunidadese.html', {
        'usuario': request.user,
        'nome_usuario': nome_do_usuario(request),
        'oportunidades': oportunidades,
        'form': form,
        'editando': editando,
    })